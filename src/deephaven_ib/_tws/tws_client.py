"""An IB TWS client that produces Deephaven tables."""

import time
from threading import Thread
from typing import Set, Union

from ibapi import news
from ibapi.client import EClient
from ibapi.commission_report import CommissionReport
from ibapi.common import *
from ibapi.contract import Contract, ContractDetails
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.ticktype import TickType, TickTypeEnum
from ibapi.wrapper import EWrapper

from .contract_registry import ContractRegistry
from .ib_type_logger import *
from .order_id_queue import OrderIdEventQueue
from .._internal.error_codes import load_error_codes
from .._internal.requests import next_unique_id
from .._internal.short_rates import load_short_rates
from .._internal.tablewriter import TableWriter
from ..time import unix_sec_to_dh_datetime

_error_code_message_map, _error_code_note_map = load_error_codes()
_news_msgtype_map: Dict[int, str] = {news.NEWS_MSG: "NEWS", news.EXCHANGE_AVAIL_MSG: "EXCHANGE_AVAILABLE",
                                     news.EXCHANGE_UNAVAIL_MSG: "EXCHANGE_UNAVAILABLE"}


# noinspection PyPep8Naming
class IbTwsClient(EWrapper, EClient):
    """A client for communicating with IB TWS.

    Almost all of the methods in this class are listeners for EWrapper and should not be called directly by users of the class.
    """

    _table_writers: Dict[str, TableWriter]
    tables: Dict[str, Any]  # TODO: should be Dict[str, Table] with deephaven v2
    _thread: Thread
    contract_registry: ContractRegistry
    _order_id_queue: OrderIdEventQueue
    _registered_market_rules: Set[str]
    _realtime_bar_sizes: Dict[TickerId, int]

    def __init__(self, download_short_rates=True):
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)
        self._table_writers = IbTwsClient._build_table_writers()
        self.tables = {name: tw.table() for (name, tw) in self._table_writers.items()}
        self._thread = None
        self.contract_registry = None
        self._order_id_queue = None
        self._registered_market_rules = None
        self._realtime_bar_sizes = None

        if download_short_rates:
            self.tables["short_rates"] = load_short_rates()

    @staticmethod
    def _build_table_writers() -> Dict[str, TableWriter]:
        # noinspection PyDictCreation
        table_writers = {}

        ####
        # General
        ####

        table_writers["requests"] = TableWriter(["RequestId", "RequestType", *logger_contract.names(), "Note"],
                                                [dht.int32, dht.string, *logger_contract.types(), dht.string])

        table_writers["errors"] = TableWriter(
            ["RequestId", "ErrorCode", "ErrorDescription", "Error", "Note"],
            [dht.int32, dht.int32, dht.string, dht.string, dht.string])

        ####
        # Contracts
        ####

        table_writers["contracts_details"] = TableWriter(
            ["RequestId", *logger_contract_details.names()],
            [dht.int32, *logger_contract_details.types()])

        table_writers["contracts_matching"] = TableWriter(
            ["RequestId", *logger_contract.names(), "DerivativeSecTypes"],
            [dht.int32, *logger_contract.types(), dht.string])

        table_writers["market_rules"] = TableWriter(
            ["MarketRuleId", *logger_price_increment.names()],
            [dht.string, *logger_price_increment.types()])

        ####
        # Accounts
        ####

        table_writers["accounts_managed"] = TableWriter(["Account"], [dht.string])

        table_writers["accounts_family_codes"] = TableWriter(
            [*logger_family_code.names()],
            [*logger_family_code.types()])

        table_writers["accounts_value"] = TableWriter(
            ["Account", "Currency", "Key", "Value"],
            [dht.string, dht.string, dht.string, dht.string])

        table_writers["accounts_portfolio"] = TableWriter(
            ["Account", *logger_contract.names(), "Position", "MarketPrice", "MarketValue", "AvgCost",
             "UnrealizedPnl", "RealizedPnl"],
            [dht.string, *logger_contract.types(), dht.float64, dht.float64, dht.float64, dht.float64,
             dht.float64, dht.float64])

        table_writers["accounts_summary"] = TableWriter(
            ["ReqId", "Account", "Tag", "Value", "Currency"],
            [dht.int32, dht.string, dht.string, dht.string, dht.string])

        table_writers["accounts_positions"] = TableWriter(
            ["Account", *logger_contract.names(), "Position", "AvgCost"],
            [dht.string, *logger_contract.types(), dht.float64, dht.float64])

        table_writers["accounts_pnl"] = TableWriter(
            ["RequestId", "DailyPnl", "UnrealizedPnl", "RealizedPnl"],
            [dht.int32, dht.float64, dht.float64, dht.float64])

        ####
        # News
        ####

        table_writers["news_providers"] = TableWriter(logger_news_provider.names(), logger_news_provider.types())

        table_writers["news_bulletins"] = TableWriter(
            ["MsgId", "MsgType", "Message", "OriginExch"],
            [dht.int32, dht.string, dht.string, dht.string])

        table_writers["news_articles"] = TableWriter(
            ["RequestId", "ArticleType", "ArticleText"],
            [dht.int32, dht.string, dht.string])

        table_writers["news_historical"] = TableWriter(
            ["RequestId", "Timestamp", "ProviderCode", "ArticleId", "Headline"],
            [dht.int32, dht.datetime, dht.string, dht.string, dht.string])

        ####
        # Market Data
        ####

        table_writers["ticks_price"] = TableWriter(
            ["RequestId", "TickType", "Price", *logger_tick_attrib.names()],
            [dht.int32, dht.string, dht.float64, *logger_tick_attrib.types()])

        table_writers["ticks_size"] = TableWriter(
            ["RequestId", "TickType", "Size"],
            [dht.int32, dht.string, dht.int32])

        table_writers["ticks_string"] = TableWriter(
            ["RequestId", "TickType", "Value"],
            [dht.int32, dht.string, dht.string])

        # exchange for physical
        table_writers["ticks_efp"] = TableWriter(
            ["RequestId", "TickType", "BasisPoints", "FormattedBasisPoints", "TotalDividends", "HoldDays",
             "FutureLastTradeDate", "DividendImpact", "DividendsToLastTradeDate"],
            [dht.int32, dht.string, dht.float64, dht.string, dht.float64, dht.int32,
             dht.string, dht.float64, dht.float64])

        table_writers["ticks_generic"] = TableWriter(
            ["RequestId", "TickType", "Value"],
            [dht.int32, dht.string, dht.float64])

        table_writers["ticks_option_computation"] = TableWriter(
            ["RequestId", "TickType", "TickAttrib", "ImpliedVol", "Delta", "OptPrice", "PvDividend", "Gamma",
             "Vega", "Theta", "UndPrice"],
            [dht.int32, dht.string, dht.string, dht.float64, dht.float64, dht.float64, dht.float64, dht.float64,
             dht.float64, dht.float64, dht.float64])

        table_writers["ticks_trade"] = TableWriter(
            ["RequestId", *logger_hist_tick_last.names()],
            [dht.int32, *logger_hist_tick_last.types()])

        table_writers["ticks_bid_ask"] = TableWriter(
            ["RequestId", *logger_hist_tick_bid_ask.names()],
            [dht.int32, *logger_hist_tick_bid_ask.types()])

        table_writers["ticks_mid_point"] = TableWriter(
            ["RequestId", "Timestamp", "MidPoint"],
            [dht.int32, dht.datetime, dht.float64])

        table_writers["bars_historical"] = TableWriter(
            ["RequestId", *logger_bar_data.names()],
            [dht.int32, *logger_bar_data.types()])

        table_writers["bars_realtime"] = TableWriter(
            ["RequestId", *logger_real_time_bar_data.names()],
            [dht.int32, *logger_real_time_bar_data.types()])

        ####
        # Order Management System (OMS)
        ####

        table_writers["orders_open"] = TableWriter(
            [*logger_contract.names(), *logger_order.names(), *logger_order_state.names()],
            [*logger_contract.types(), *logger_order.types(), *logger_order_state.types()])

        table_writers["orders_status"] = TableWriter(
            ["OrderId", "Status", "Filled", "Remaining", "AvgFillPrice", "PermId", "ParentId", "LastFillPrice",
             "ClientId", "WhyHeld", "MktCapPrice"],
            [dht.int32, dht.string, dht.float64, dht.float64, dht.float64, dht.int32, dht.int32, dht.float64,
             dht.int32, dht.string, dht.float64])

        table_writers["orders_completed"] = TableWriter(
            [*logger_contract.names(), *logger_order.names(), *logger_order_state.names()],
            [*logger_contract.types(), *logger_order.types(), *logger_order_state.types()])

        table_writers["orders_exec_details"] = TableWriter(
            ["ReqId", *logger_contract.names(renames={"Exchange": "ContractExchange"}),
             *logger_execution.names(renames={"Exchange": "ExecutionExchange"})],
            [dht.int32, *logger_contract.types(), *logger_execution.types()])

        table_writers["orders_exec_commission_report"] = TableWriter(
            [*logger_commission_report.names()],
            [*logger_commission_report.types()])

        ####
        # End
        ####

        return table_writers

    ####################################################################################################################
    ####################################################################################################################
    ## Connect / Disconnect / Subscribe
    ####################################################################################################################
    ####################################################################################################################

    def connect(self, host: str, port: int, client_id: int) -> None:
        """Connect to an IB TWS session.  Raises an exception if already connected.

        Args:
            host (str): The host name or IP address of the machine where TWS is running. Leave blank to connect to the local host.
            port (int): TWS port, specified in TWS on the Configure>API>Socket Port field.
                By default production trading uses port 7496 and paper trading uses port 7497.
            client_id (int): A number used to identify this client connection.
                All orders placed/modified from this client will be associated with this client identifier.

                Note: Each client MUST connect with a unique clientId.

        Returns:
              None

        Raises:
              Exception
        """

        if self.isConnected():
            raise Exception("IbTwsClient is already connected.")

        EClient.connect(self, host, port, client_id)

        # wait for the client to connect to avoid a race condition
        time.sleep(1)

        self._thread = Thread(target=self.run)
        self._thread.start()
        setattr(self, "ib_thread", self._thread)

        # wait for the client to connect to avoid a race condition
        time.sleep(1)

        self._subscribe()

        # wait for the client to connect to avoid a race condition
        time.sleep(1)

    def disconnect(self) -> None:
        """Disconnect from an IB TWS session.

        Returns:
            None
        """

        EClient.disconnect(self)
        self._thread = None
        self.contract_registry = None
        self._order_id_queue = None
        self._registered_market_rules = None
        self._realtime_bar_sizes = None

    def _subscribe(self) -> None:
        """Subscribe to IB data."""

        self.contract_registry = ContractRegistry(self)
        self._order_id_queue = OrderIdEventQueue()
        self._registered_market_rules = set()
        self._realtime_bar_sizes = {}

        account_summary_tags = [
            "accountountType",
            "NetLiquidation",
            "TotalCashValue",
            "SettledCash",
            "TotalCashValue",
            "AccruedCash",
            "BuyingPower",
            "EquityWithLoanValue",
            "PreviousDayEquityWithLoanValue",
            "GrossPositionValue",
            "RegTEquity",
            "RegTMargin",
            "SMA",
            "InitMarginReq",
            "MaintMarginReq",
            "AvailableFunds",
            "ExcessLiquidity",
            "Cushion",
            "FullInitMarginReq",
            "FullMaintMarginReq",
            "FullAvailableFunds",
            "FullExcessLiquidity",
            "LookAheadNextChange",
            "LookAheadInitMarginReq",
            "LookAheadMaintMarginReq",
            "LookAheadAvailableFunds",
            "LookAheadExcessLiquidity",
            "HighestSeverity",
            "DayTradesRemaining",
            "Leverage",
            "$LEDGER",
        ]

        self.reqManagedAccts()
        req_id = next_unique_id()
        tags = ",".join(account_summary_tags)
        self.log_request(req_id, "AccountSummary", None, f"groupName='All' tags={tags}")
        self.reqAccountSummary(reqId=req_id, groupName="All", tags=tags)
        self.reqPositions()
        self.reqNewsBulletins(allMsgs=True)
        req_id = next_unique_id()
        self.log_request(req_id, "Executions", None, None)
        self.reqExecutions(reqId=next_unique_id(), execFilter=ExecutionFilter())
        self.reqCompletedOrders(apiOnly=False)
        self.reqNewsProviders()
        self.reqAllOpenOrders()
        self.reqFamilyCodes()

    ####################################################################################################################
    ####################################################################################################################
    ## General
    ####################################################################################################################
    ####################################################################################################################

    def log_request(self, req_id: int, request_type: str, contract: Union[Contract, None], note: Union[str, None]):
        """Log a data request."""
        self._table_writers["requests"].write_row([req_id, request_type, *logger_contract.vals(contract), note])

    ####
    # Always present
    ####

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        EWrapper.error(self, reqId, errorCode, errorString)
        self._table_writers["errors"].write_row(
            [reqId, errorCode, map_values(errorCode, _error_code_message_map), errorString,
             map_values(errorCode, _error_code_note_map)])

        if self.contract_registry:
            self.contract_registry.add_error_data(req_id=reqId, error_string=errorString)

    ####################################################################################################################
    ####################################################################################################################
    ## Contracts
    ####################################################################################################################
    ####################################################################################################################

    def request_market_rules(self, contractDetails: ContractDetails):
        """Request price increment market quoting rules, if they have not yet been retrieved."""

        for market_rule in contractDetails.marketRuleIds.split(","):
            if market_rule not in self._registered_market_rules:
                self.reqMarketRule(marketRuleId=int(market_rule))

    ####
    # reqContractDetails
    ####

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        EWrapper.contractDetails(self, reqId, contractDetails)
        self._table_writers["contracts_details"].write_row([reqId, *logger_contract_details.vals(contractDetails)])
        self.contract_registry.add_contract_data(reqId, contractDetails)
        self.request_market_rules(contractDetails)

    def bondContractDetails(self, reqId: int, contractDetails: ContractDetails):
        EWrapper.bondContractDetails(self, reqId, contractDetails)
        self._table_writers["contracts_details"].write_row([reqId, *logger_contract_details.vals(contractDetails)])
        self.contract_registry.add_contract_data(reqId, contractDetails)
        self.request_market_rules(contractDetails)

    def contractDetailsEnd(self, reqId: int):
        # do not ned to implement
        EWrapper.contractDetailsEnd(self, reqId)

    ####
    # reqMatchingSymbols
    ####

    def symbolSamples(self, reqId: int, contractDescriptions: ListOfContractDescription):
        EWrapper.symbolSamples(self, reqId, contractDescriptions)

        for cd in contractDescriptions:
            self._table_writers["contracts_matching"].write_row([reqId, *logger_contract.vals(cd.contract),
                                                                 to_string_set(cd.derivativeSecTypes)])
            self.contract_registry.request_contract_details_nonblocking(cd.contract)

    ####
    # reqMarketRule
    ####

    def marketRule(self, marketRuleId: int, priceIncrements: ListOfPriceIncrements):
        EWrapper.marketRule(self, marketRuleId, priceIncrements)

        for pi in priceIncrements:
            self._table_writers["market_rules"].write_row([str(marketRuleId), *logger_price_increment.vals(pi)])

        self._registered_market_rules.add(str(marketRuleId))

    ####################################################################################################################
    ####################################################################################################################
    ## Accounts
    ####################################################################################################################
    ####################################################################################################################

    ####
    # reqManagedAccts
    ####

    def managedAccounts(self, accountsList: str):
        EWrapper.managedAccounts(self, accountsList)

        for account in accountsList.split(","):
            if account:
                self._table_writers["accounts_managed"].write_row([account])
                self.reqAccountUpdates(subscribe=True, acctCode=account)

    ####
    # reqFamilyCodes
    ####

    def familyCodes(self, familyCodes: ListOfFamilyCode):
        EWrapper.familyCodes(self, familyCodes)

        for fc in familyCodes:
            self._table_writers["accounts_family_codes"].write_row(logger_family_code.vals(fc))

    ####
    # reqAccountUpdates
    ####

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        EWrapper.updateAccountValue(self, key, val, currency, accountName)
        self._table_writers["accounts_value"].write_row([accountName, currency, key, val])

    def updatePortfolio(self, contract: Contract, position: float,
                        marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float,
                        realizedPNL: float, accountName: str):
        EWrapper.updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL,
                                 realizedPNL, accountName)
        self._table_writers["accounts_portfolio"].write_row([accountName, *logger_contract.vals(contract), position,
                                                             marketPrice, marketValue, averageCost, unrealizedPNL,
                                                             realizedPNL])
        self.contract_registry.request_contract_details_nonblocking(contract)

    ####
    # reqAccountSummary
    ####

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        EWrapper.accountSummary(self, reqId, account, tag, value, currency)
        self._table_writers["accounts_summary"].write_row([reqId, account, tag, value, currency])

    ####
    # reqPositions
    ####

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        EWrapper.position(self, account, contract, position, avgCost)
        self._table_writers["accounts_positions"].write_row(
            [account, *logger_contract.vals(contract), position, avgCost])
        self.contract_registry.request_contract_details_nonblocking(contract)

    ####
    # reqPnL
    ####

    def pnl(self, reqId: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float):
        EWrapper.pnl(self, reqId, dailyPnL, unrealizedPnL, realizedPnL)
        self._table_writers["accounts_pnl"].write_row([reqId, dailyPnL, unrealizedPnL, realizedPnL])

    ####################################################################################################################
    ####################################################################################################################
    ## News
    ####################################################################################################################
    ####################################################################################################################

    ####
    # reqNewsProviders
    ####

    def newsProviders(self, newsProviders: ListOfNewsProviders):
        EWrapper.newsProviders(self, newsProviders)

        for provider in newsProviders:
            self._table_writers["news_providers"].write_row(logger_news_provider.vals(provider))

    ####
    # reqNewsBulletins
    ####

    def updateNewsBulletin(self, msgId: int, msgType: int, newsMessage: str, originExch: str):
        EWrapper.updateNewsBulletin(self, msgId, msgType, newsMessage, originExch)
        self._table_writers["news_bulletins"].write_row([msgId, map_values(msgType, _news_msgtype_map), newsMessage,
                                                         originExch])

    ####
    # reqNewsArticle
    ####

    def newsArticle(self, requestId: int, articleType: int, articleText: str):
        EWrapper.newsArticle(self, requestId, articleType, articleText)
        at = map_values(articleType, {0: "PlainTextOrHtml", 1: "BinaryDataOrPdf"})
        self._table_writers["news_articles"].write_row([requestId, at, articleText])

    ####
    # reqHistoricalNews
    ####

    def historicalNews(self, requestId: int, timestamp: str, providerCode: str, articleId: str, headline: str):
        EWrapper.historicalNews(self, requestId, timestamp, providerCode, articleId, headline)
        self._table_writers["news_historical"].write_row(
            [requestId, ib_to_dh_datetime(timestamp), providerCode, articleId,
             headline])

    def historicalNewsEnd(self, requestId: int, hasMore: bool):
        # do not need to implement
        self.historicalNewsEnd(requestId, hasMore)

    ####################################################################################################################
    ####################################################################################################################
    ## Market Data
    ####################################################################################################################
    ####################################################################################################################

    ####
    # reqMktData
    ####

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        EWrapper.tickPrice(self, reqId, tickType, price, attrib)
        self._table_writers["ticks_price"].write_row([reqId, TickTypeEnum.to_str(tickType), price,
                                                      *logger_tick_attrib.vals(attrib)])

    def tickSize(self, reqId: TickerId, tickType: TickType, size: int):
        EWrapper.tickSize(self, reqId, tickType, size)
        self._table_writers["ticks_size"].write_row([reqId, TickTypeEnum.to_str(tickType), size])

    def tickString(self, reqId: TickerId, tickType: TickType, value: str):
        EWrapper.tickString(self, reqId, tickType, value)
        self._table_writers["ticks_string"].write_row([reqId, TickTypeEnum.to_str(tickType), value])

    def tickEFP(self, reqId: TickerId, tickType: TickType, basisPoints: float,
                formattedBasisPoints: str, totalDividends: float,
                holdDays: int, futureLastTradeDate: str, dividendImpact: float,
                dividendsToLastTradeDate: float):
        EWrapper.tickEFP(self, reqId, tickType, basisPoints, formattedBasisPoints, totalDividends, holdDays,
                         futureLastTradeDate, dividendImpact, dividendsToLastTradeDate)
        self._table_writers["ticks_efp"].write_row(
            [reqId, TickTypeEnum.to_str(tickType), basisPoints, formattedBasisPoints,
             totalDividends, holdDays, futureLastTradeDate, dividendImpact,
             dividendsToLastTradeDate])

    def tickGeneric(self, reqId: TickerId, tickType: TickType, value: float):
        EWrapper.tickGeneric(self, reqId, tickType, value)
        self._table_writers["ticks_generic"].write_row([reqId, TickTypeEnum.to_str(tickType), value])

    def tickOptionComputation(self, reqId: TickerId, tickType: TickType, tickAttrib: int,
                              impliedVol: float, delta: float, optPrice: float, pvDividend: float,
                              gamma: float, vega: float, theta: float, undPrice: float):
        EWrapper.tickOptionComputation(self, reqId, tickType, tickAttrib, impliedVol, delta, optPrice, pvDividend,
                                       gamma, vega, theta, undPrice)
        ta = map_values(tickAttrib, {0: "Return-based", 1: "Price-based"})
        self._table_writers["ticks_option_computation"].write_row([reqId, TickTypeEnum.to_str(tickType), ta, impliedVol,
                                                                   delta,
                                                                   optPrice, pvDividend, gamma, vega, theta, undPrice])

    def tickSnapshotEnd(self, reqId: int):
        # do not ned to implement
        EWrapper.tickSnapshotEnd(self, reqId)

    ####
    # reqTickByTickData and reqHistoricalTicks
    ####

    def tickByTickAllLast(self, reqId: int, tickType: int, timestamp: int, price: float,
                          size: int, tickAttribLast: TickAttribLast, exchange: str,
                          specialConditions: str):
        EWrapper.tickByTickAllLast(self, reqId, tickType, timestamp, price, size, tickAttribLast, exchange,
                                   specialConditions)

        t = HistoricalTickLast()
        t.time = timestamp
        t.tickAttribLast = tickAttribLast
        t.price = price
        t.size = size
        t.exchange = exchange
        t.specialConditions = specialConditions

        self._table_writers["ticks_trade"].write_row([reqId, *logger_hist_tick_last.vals(t)])

    # noinspection PyUnusedLocal
    def historicalTicksLast(self, reqId: int, ticks: ListOfHistoricalTickLast, done: bool):
        EWrapper.historicalTicksLast(self, reqId, ticks, done)

        for t in ticks:
            self._table_writers["ticks_trade"].write_row([reqId, *logger_hist_tick_last.vals(t)])

    def tickByTickBidAsk(self, reqId: int, timestamp: int, bidPrice: float, askPrice: float,
                         bidSize: int, askSize: int, tickAttribBidAsk: TickAttribBidAsk):
        EWrapper.tickByTickBidAsk(self, reqId, timestamp, bidPrice, askPrice, bidSize, askSize, tickAttribBidAsk)

        t = HistoricalTickBidAsk()
        t.time = timestamp
        t.tickAttribBidAsk = tickAttribBidAsk
        t.priceBid = bidPrice
        t.priceAsk = askPrice
        t.sizeBid = bidSize
        t.sizeAsk = askSize

        self._table_writers["ticks_bid_ask"].write_row([reqId, *logger_hist_tick_bid_ask.vals(t)])

    def historicalTicksBidAsk(self, reqId: int, ticks: ListOfHistoricalTickBidAsk, done: bool):

        for t in ticks:
            self._table_writers["ticks_bid_ask"].write_row([reqId, *logger_hist_tick_bid_ask.vals(t)])

    def tickByTickMidPoint(self, reqId: int, timestamp: int, midPoint: float):
        EWrapper.tickByTickMidPoint(self, reqId, timestamp, midPoint)
        self._table_writers["ticks_mid_point"].write_row([reqId, unix_sec_to_dh_datetime(timestamp), midPoint])

    def historicalTicks(self, reqId: int, ticks: ListOfHistoricalTick, done: bool):
        EWrapper.historicalTicks(self, reqId, ticks, done)

        for t in ticks:
            self._table_writers["ticks_mid_point"].write_row([reqId, unix_sec_to_dh_datetime(t.time), t.price])

    ####
    # reqHistoricalData
    ####

    def historicalData(self, reqId: int, bar: BarData):
        EWrapper.historicalData(self, reqId, bar)
        self._table_writers["bars_historical"].write_row([reqId, *logger_bar_data.vals(bar)])

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        # do not ned to implement
        EWrapper.historicalDataEnd(self, reqId, start, end)

    ####
    # reqRealTimeBars
    ####

    def reqRealTimeBars(self, reqId: TickerId, contract: Contract, barSize: int,
                        whatToShow: str, useRTH: bool,
                        realTimeBarsOptions: TagValueList):
        self._realtime_bar_sizes[reqId] = barSize
        EClient.reqRealTimeBars(self, reqId, contract, barSize, whatToShow, useRTH, realTimeBarsOptions)

    def realtimeBar(self, reqId: TickerId, timestamp: int, open_: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        EWrapper.realtimeBar(self, reqId, timestamp, open_, high, low, close, volume, wap, count)
        bar_size = self._realtime_bar_sizes[reqId]
        bar = RealTimeBar(time=timestamp, endTime=timestamp + bar_size, open_=open_, high=high, low=low, close=close,
                          volume=volume,
                          wap=wap, count=count)
        self._table_writers["bars_realtime"].write_row([reqId, *logger_real_time_bar_data.vals(bar)])

    ####################################################################################################################
    ####################################################################################################################
    ## Order Management System (OMS)
    ####################################################################################################################
    ####################################################################################################################

    def next_order_id(self) -> int:
        """Gets the next valid order ID."""
        request = self._order_id_queue.request()
        self.reqIds(-1)
        return request.get()

    ####
    # reqIds
    ####

    def nextValidId(self, orderId: int):
        EWrapper.nextValidId(self, orderId)

        if self._order_id_queue:
            self._order_id_queue.add_value(orderId)

    ####
    # reqAllOpenOrders
    ####

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        EWrapper.openOrder(self, orderId, contract, order, orderState)

        if orderId != order.orderId:
            raise Exception("Order IDs do not match")

        self._table_writers["orders_open"].write_row(
            [*logger_contract.vals(contract), *logger_order.vals(order), *logger_order_state.vals(orderState)])
        self.contract_registry.request_contract_details_nonblocking(contract)

    def orderStatus(self, orderId: OrderId, status: str, filled: float,
                    remaining: float, avgFillPrice: float, permId: int,
                    parentId: int, lastFillPrice: float, clientId: int,
                    whyHeld: str, mktCapPrice: float):
        EWrapper.orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice,
                             clientId, whyHeld, mktCapPrice)
        self._table_writers["orders_status"].write_row(
            [orderId, status, filled, remaining, avgFillPrice, permId, parentId,
             lastFillPrice, clientId, whyHeld, mktCapPrice])

    def openOrderEnd(self):
        # do not ned to implement
        EWrapper.openOrderEnd(self)

    ####
    # reqCompletedOrders
    ####

    def completedOrder(self, contract: Contract, order: Order, orderState: OrderState):
        EWrapper.completedOrder(self, contract, order, orderState)
        self._table_writers["orders_completed"].write_row([*logger_contract.vals(contract), *logger_order.vals(order),
                                                           *logger_order_state.vals(orderState)])
        self.contract_registry.request_contract_details_nonblocking(contract)

    def completedOrdersEnd(self):
        # do not ned to implement
        EWrapper.completedOrdersEnd(self)

    ####
    # reqExecutions
    ####

    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        EWrapper.execDetails(self, reqId, contract, execution)
        self._table_writers["orders_exec_details"].write_row([reqId, *logger_contract.vals(contract),
                                                              *logger_execution.vals(execution)])
        self.contract_registry.request_contract_details_nonblocking(contract)

    def execDetailsEnd(self, reqId: int):
        # do not need to implement
        EWrapper.execDetailsEnd(self, reqId)

    def commissionReport(self, commissionReport: CommissionReport):
        EWrapper.commissionReport(self, commissionReport)
        self._table_writers["orders_exec_commission_report"].write_row(logger_commission_report.vals(commissionReport))

    ####################################################################################################################
    ####################################################################################################################
    ## End
    ####################################################################################################################
    ####################################################################################################################
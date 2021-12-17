import logging

from deephaven import DynamicTableWriter, Types as dht
from ibapi import news
from ibapi.commission_report import CommissionReport
from ibapi.common import ListOfNewsProviders, OrderId
from ibapi.contract import Contract
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.wrapper import EWrapper

from ._client import _IbClient
from ._ibtypelogger import IbContractLogger, IbOrderLogger, IbOrderStateLogger
from ..utils import next_unique_id

logging.basicConfig(level=logging.DEBUG)

_ib_contract_logger = IbContractLogger()
_ib_order_logger = IbOrderLogger()
_ib_order_state_logger = IbOrderStateLogger()


# TODO: map string "" to None
# TODO: parse time strings

# TODO: no users need to see this
class _IbListener(EWrapper):
    """Listener for data from IB."""

    def __init__(self):
        EWrapper.__init__(self)
        self._client = None
        self.account_value = DynamicTableWriter(["Account", "Currency", "Key", "Value"],
                                                [dht.string, dht.string, dht.string, dht.string])
        self.portfolio = DynamicTableWriter(
            ["Account", *_ib_contract_logger.names(), "Position", "MarketPrice", "MarketValue", "AvgCost",
             "UnrealizedPnl", "RealizedPnl"],
            [dht.string, *_ib_contract_logger.types(), dht.float64, dht.float64, dht.float64, dht.float64,
             dht.float64, dht.float64])

        self.account_summary = DynamicTableWriter(["ReqId", "Account", "Tag", "Value", "Currency"],
                                                  [dht.int64, dht.string, dht.string, dht.string, dht.string])

        self.positions = DynamicTableWriter(["Account", *_ib_contract_logger.names(), "Position", "AvgCost"],
                                            [dht.string, *_ib_contract_logger.types(), dht.float64, dht.float64])

        self.news_bulletins = DynamicTableWriter(["MsgId", "MsgType", "Message", "OriginExch"],
                                                 [dht.int64, dht.string, dht.string, dht.string])

        self.exec_details = DynamicTableWriter(["ReqId", "Time", "Account", *_ib_contract_logger.names(),
                                                "Exchange", "Side", "Shares", "Price",
                                                "CumQty", "AvgPrice", "Liquidation",
                                                "EvRule", "EvMultiplier", "ModelCode", "LastLiquidity"
                                                                                       "ExecId", "PermId", "ClientId",
                                                "OrderId", "OrderRef"],
                                               [dht.int64, dht.string, dht.string, *_ib_contract_logger.types(),
                                                dht.string, dht.string, dht.float64, dht.float64,
                                                dht.float64, dht.float64, dht.int64,
                                                dht.string, dht.float64, dht.string, dht.int64,
                                                dht.string, dht.int64, dht.int64, dht.int64, dht.string])

        self.commission_report = DynamicTableWriter(
            ["ExecId", "Currency", "Commission", "RealizedPnl", "Yield", "YieldRedemptionDate"],
            [dht.string, dht.string, dht.float64, dht.float64, dht.float64, dht.int64])

        self.news_providers = DynamicTableWriter(["Provider"], [dht.string])

        self.orders_completed = DynamicTableWriter(
            [*_ib_contract_logger.names(), *_ib_order_logger.names(), *_ib_order_state_logger.names()],
            [*_ib_contract_logger.types(), *_ib_order_logger.types(), *_ib_order_state_logger.types()])

        self.orders_status = DynamicTableWriter(
            ["OrderId", "Status", "Filled", "Remaining", "AvgFillPrice", "PermId", "ParentId", "LastFillPrice",
             "ClientId", "WhyHeld", "MktCapPrice"],
            [dht.int64, dht.string, dht.float64, dht.float64, dht.float64, dht.int64, dht.int64, dht.float64, dht.int64,
             dht.string, dht.float64])

        self.orders_open = DynamicTableWriter(
            ["OrderId", *_ib_contract_logger.names(), *_ib_order_logger.names(), *_ib_order_state_logger.names()],
            [dht.int64, *_ib_contract_logger.types(), *_ib_order_logger.types(), *_ib_order_state_logger.types()])

        self.historical_news = DynamicTableWriter(
            ["RequestId", "Time", "ProviderCode", "ArticleId", "Headline"],
            [dht.int64, dht.string, dht.string, dht.string, dht.string])


    def connect(self, client: _IbClient):
        self._client = client

        client.reqManagedAccts()

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

        client.reqAccountSummary(reqId=next_unique_id(), groupName="All", tags=",".join(account_summary_tags))
        client.reqPositions()
        client.reqNewsBulletins(allMsgs=True)
        client.reqExecutions(reqId=next_unique_id(), execFilter=ExecutionFilter())
        client.reqCompletedOrders(apiOnly=False)
        client.reqNewsProviders()
        client.reqAllOpenOrders()


    def disconnect(self):
        self._client = None



    ####
    # reqManagedAccts
    ####

    def managedAccounts(self, accountsList: str):
        EWrapper.managedAccounts(self, accountsList)

        for account in accountsList.split(","):
            self._client.reqAccountUpdates(subscribe=True, acctCode=account)

    ####
    # reqAccountUpdates
    ####

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        EWrapper.updateAccountValue(key, val, currency, accountName)
        self.account_value.logRow(accountName, currency, key, val)

    def updatePortfolio(self, contract: Contract, position: float,
                        marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float,
                        realizedPNL: float, accountName: str):
        EWrapper.updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL,
                                 realizedPNL, accountName)
        self.portfolio.logRow(accountName, *_ib_contract_logger.vals(contract), position, marketPrice, marketValue,
                              averageCost, unrealizedPNL, realizedPNL)

    ####
    # reqAccountSummary
    ####

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        EWrapper.accountSummary(self, reqId, account, tag, value, currency)
        self.account_summary.logRow(reqId, account, tag, value, currency)

    ####
    # reqPositions
    ####

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        EWrapper.position(account, contract, position, avgCost)
        self.positions.logRow(account, *_ib_contract_logger.vals(contract), position, avgCost)

    ####
    # reqNewsBulletins
    ####

    def updateNewsBulletin(self, msgId: int, msgType: int, newsMessage: str, originExch: str):
        EWrapper.updateNewsBulletin(msgId, msgType, newsMessage, originExch)

        if msgType == news.NEWS_MSG:
            mtype = "NEWS"
        elif msgType == news.EXCHANGE_AVAIL_MSG:
            mtype = "EXCHANGE_AVAILABLE"
        elif msgType == news.EXCHANGE_UNAVAIL_MSG:
            mtype = "EXCHANGE_UNAVAILABLE"
        else:
            mtype = f"UNKNOWN({msgType})"

        self.news_bulletins.logRow(msgId, mtype, newsMessage, originExch)

    ####
    # reqExecutions
    ####

    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        EWrapper.execDetails(self, reqId, contract, execution)
        self.exec_details.logRow(reqId, execution.time, execution.acctNumber, *_ib_contract_logger.vals(contract),
                                 execution.exchange, execution.side, execution.shares, execution.price,
                                 execution.cumQty, execution.avgPrice, execution.liquidation,
                                 execution.evRule, execution.evMultiplier, execution.modelCode, execution.lastLiquidity,
                                 execution.execId, execution.permId, execution.clientId, execution.orderId,
                                 execution.orderRef)

    def execDetailsEnd(self, reqId: int):
        # do not need to implement
        EWrapper.execDetailsEnd(self, reqId)

    def commissionReport(self, commissionReport: CommissionReport):
        EWrapper.commissionReport(self, commissionReport)
        self.commission_report.logRow(commissionReport.execId, commissionReport.currency, commissionReport.commission,
                                      commissionReport.realizedPNL, commissionReport.yield_,
                                      commissionReport.yieldRedemptionDate)

    ####
    # reqNewsProviders
    ####

    def newsProviders(self, newsProviders: ListOfNewsProviders):
        EWrapper.newsProviders(self, newsProviders)

        for provider in newsProviders:
            self.news_providers.logRow(provider)

    ####
    # reqCompletedOrders
    ####

    def completedOrder(self, contract: Contract, order: Order, orderState: OrderState):
        EWrapper.completedOrder(self, contract, order, orderState)
        self.orders_completed.logRow(*_ib_contract_logger.vals(contract), *_ib_order_logger.vals(order),
                                     *_ib_order_state_logger.vals(orderState))

    def completedOrdersEnd(self):
        # do not ned to implement
        EWrapper.completedOrdersEnd(self)

    ####
    # reqAllOpenOrders
    ####

    def orderStatus(self, orderId: OrderId, status: str, filled: float,
                    remaining: float, avgFillPrice: float, permId: int,
                    parentId: int, lastFillPrice: float, clientId: int,
                    whyHeld: str, mktCapPrice: float):
        EWrapper.orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice,
                             clientId, whyHeld, mktCapPrice)
        self.orders_status.logRow(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice,
                                  clientId, whyHeld, mktCapPrice)

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        EWrapper.openOrder(orderId, contract, order, orderState)
        self.orders_open.logRow(orderId, *_ib_contract_logger.vals(contract), *_ib_order_logger.vals(order),
                                *_ib_order_state_logger.vals(orderState))

    def openOrderEnd(self):
        # do not ned to implement
        EWrapper.openOrderEnd(self)

    ####
    # reqHistoricalNews
    ####

    def historicalNews(self, requestId: int, time: str, providerCode: str, articleId: str, headline: str):
        EWrapper.historicalNews(requestId, time, providerCode, articleId, headline)
        self.historical_news.logRow(requestId, time, providerCode, articleId, headline)

    def historicalNewsEnd(self, requestId: int, hasMore: bool):
        # do not ned to implement
        self.historicalNewsEnd(requestId, hasMore)

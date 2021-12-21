from typing import Any, List, Tuple

from deephaven import Types as dht

from .._logging_utils import map_values, to_string_val, to_string_set
from ..utils import unix_sec_to_dh_datetime


class IbComplexTypeLogger:
    """ Base class for logging complex IB types. """

    def __init__(self, column_details: List[Tuple]):
        self.column_details = column_details

    def names(self) -> List[str]:
        """ Column names. """
        return [cd[0] for cd in self.column_details]

    def types(self) -> List[Any]:
        """ Column types. """
        return [cd[1] for cd in self.column_details]

    def vals(self, ib_obj: Any) -> List[Any]:
        """ Column values extracted from the IB object. """
        return [cd[2](ib_obj) for cd in self.column_details]


class IbContractLogger(IbComplexTypeLogger):
    """ Logging for IB Contracts. """

    def __init__(self):
        column_details = [
            ("ContractId", dht.int64, lambda contract: contract.conId),
            ("SecId", dht.string, lambda contract: contract.secId),
            ("SecIdType", dht.string, lambda contract: contract.secIdType),
            ("SecType", dht.string, lambda contract: contract.secType),
            ("Symbol", dht.string, lambda contract: contract.symbol),
            ("LocalSymbol", dht.string, lambda contract: contract.localSymbol),
            ("TradingClass", dht.string, lambda contract: contract.tradingClass),
            ("Currency", dht.string, lambda contract: contract.currency),
            ("Exchange", dht.string, lambda contract: contract.exchange),
            ("PrimaryExchange", dht.string, lambda contract: contract.primaryExchange),
            ("LastTradeDateOrContractMonth", dht.string, lambda contract: contract.lastTradeDateOrContractMonth),
            ("Strike", dht.float64, lambda contract: contract.strike),
            ("Right", dht.string, lambda contract: contract.right),
            ("Multiplier", dht.string, lambda contract: contract.multiplier),

            # combos
            ("ComboLegsDescrip", dht.string, lambda contract: contract.comboLegsDescrip),
            ("ComboLegs", dht.stringset, lambda contract: to_string_set(contract.comboLegs)),
            ("DeltaNeutralContract", dht.string, lambda contract: to_string_val(contract.deltaNeutralContract)),
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbOrderLogger(IbComplexTypeLogger):
    """ Logging for IB Orders. """

    def __init__(self):
        oca_types = {1: "CancelL_With_Block", 2: "Reduce_With_Block", 3: "Reduce_Non_Block"}
        trigger_methods = {0: "Default", 1: "Double_Bid_Ask", 2: "Last", 3: "Double_Last", 4: "Bid_Ask",
                           7: "Last_or_Bid_Ask", 8: "Mid-point"}
        rule80_values = {"I": "Individual", "A": "Agency", "W": "AgentOtherMember", "J": "IndividualPTIA",
                         "U": "AgencyPTIA", "M": "AgentOtherMemberPTIA", "K": "IndividualPT", "Y": "AgencyPT",
                         "N": "AgentOtherMemberPT"}
        open_close_values = {"O": "Open", "C": "Close"}
        origin_values = {0: "Customer", 1: "Firm", 2: "Unknown"}
        short_sale_slot_values = {1: "Holding", 2: "Elsewhere"}
        volatility_type = {1: "Daily", 2: "Annual"}
        reference_price_type = {1: "Average", 2: "BidOrAsk"}
        hedge_type = {"D": "Delta", "B": "Beta", "F": "FX", "P": "Pair"}
        auction_stragey_values = {0: "Unset", 1: "Match", 2: "Improvement", 3: "Transparent"}

        column_details = [

            # order identifier
            ("OrderId", dht.int64, lambda o: o.orderId),
            ("ClientId", dht.int64, lambda o: o.clientId),
            ("PermId", dht.int64, lambda o: o.permId),

            # main order fields
            ("Action", dht.string, lambda o: o.action),
            ("TotalQuantity", dht.int64, lambda o: o.totalQuantity),
            ("OrderType", dht.string, lambda o: o.orderType),
            ("LmtPrice", dht.float64, lambda o: o.lmtPrice),
            ("AuxPrice", dht.float64, lambda o: o.auxPrice),

            # extended order fields
            ("TIF", dht.string, lambda o: o.tif),
            ("ActiveStartTime", dht.string, lambda o: o.activeStartTime),
            ("ActiveStopTime", dht.string, lambda o: o.activeStopTime),
            ("OcaGroup", dht.string, lambda o: o.ocaGroup),
            ("OcaType", dht.string, lambda o: map_values(o.ocaType, oca_types)),
            ("OrderRef", dht.string, lambda o: o.orderRef),
            ("Transmit", dht.bool_, lambda o: o.transmit),
            ("ParentId", dht.int64, lambda o: o.parentId),
            ("BlockOrder", dht.bool_, lambda o: o.blockOrder),
            ("SweepToFill", dht.bool_, lambda o: o.sweepToFill),
            ("DisplaySize", dht.int64, lambda o: o.displaySize),
            ("TriggerMethod", dht.string, lambda o: map_values(o.triggerMethod, trigger_methods)),
            ("OutsideRth", dht.bool_, lambda o: o.outsideRth),
            ("Hidden", dht.bool_, lambda o: o.hidden),
            ("GoodAfterTime", dht.string, lambda o: o.goodAfterTime),
            ("GoodTillDate", dht.string, lambda o: o.goodTillDate),
            ("Rule80A", dht.string, lambda o: map_values(o.rule80A, rule80_values)),
            ("AllOrNone", dht.bool_, lambda o: o.allOrNone),
            ("MinQty", dht.int64, lambda o: o.minQty),
            ("PercentOffset", dht.float64, lambda o: o.percentOffset),
            ("OverridePercentageConstraints", dht.bool_, lambda o: o.overridePercentageConstraints),
            ("TrailStopPrice", dht.float64, lambda o: o.trailStopPrice),
            ("TrailingPercent", dht.float64, lambda o: o.trailingPercent),

            # financial advisors only
            ("FaGroup", dht.string, lambda o: o.faGroup),
            ("FaProfile", dht.string, lambda o: o.faProfile),
            ("FaMethod", dht.string, lambda o: o.faMethod),
            ("FaPercentage", dht.string, lambda o: o.faPercentage),

            # institutional (ie non-cleared) only
            ("DesignatedLocation", dht.string, lambda o: o.designatedLocation),
            ("OpenClose", dht.string, lambda o: map_values(o.openClose, open_close_values)),
            ("Origin", dht.string, lambda o: map_values(o.origin, origin_values)),
            ("ShortSaleSlot", dht.string, lambda o: map_values(o.shortSaleSlot, short_sale_slot_values)),
            ("ExemptClode", dht.int64, lambda o: o.exemptCode),

            # SMART routing only
            ("DiscretionaryAmt", dht.int64, lambda o: o.discretionaryAmt),
            ("ETradeOnly", dht.bool_, lambda o: o.eTradeOnly),
            ("FirmQuoteOnly", dht.bool_, lambda o: o.firmQuoteOnly),
            ("NbboPriceCap", dht.float64, lambda o: o.nbboPriceCap),
            ("OptOutSmarRouting", dht.bool_, lambda o: o.optOutSmartRouting),

            # BOX exchange orders only
            ("AuctionStrategy", dht.string, lambda o: map_values(o.auctionStrategy, auction_stragey_values)),
            ("StartingPrice", dht.float64, lambda o: o.startingPrice),
            ("StockRefPrice", dht.float64, lambda o: o.stockRefPrice),
            ("Delta", dht.float64, lambda o: o.delta),

            # pegged to stock and VOL orders only
            ("StockRangeLower", dht.float64, lambda o: o.stockRangeLower),
            ("StockRangeUpper", dht.float64, lambda o: o.stockRangeUpper),

            ("RandomizePrice", dht.bool_, lambda o: o.randomizePrice),
            ("RandomizeSize", dht.bool_, lambda o: o.randomizeSize),

            # VOLATILITY ORDERS ONLY
            ("Volatility", dht.float64, lambda o: o.volatility),
            ("VolatilityType", dht.string, lambda o: map_values(o.volatilityType, volatility_type)),
            ("DeltaNeutralOrderType", dht.string, lambda o: o.deltaNeutralOrderType),
            ("DeltaNeutralAuxPrice", dht.float64, lambda o: o.deltaNeutralAuxPrice),
            ("DeltaNeutralConId", dht.int64, lambda o: o.deltaNeutralConId),
            ("DeltaNeutralSettlingFirm", dht.string, lambda o: o.deltaNeutralSettlingFirm),
            ("DeltaNeutralClearingAccount", dht.string, lambda o: o.deltaNeutralClearingAccount),
            ("DeltaNeutralClearingIntent", dht.string, lambda o: o.deltaNeutralClearingIntent),
            ("DeltaNeutralOpenClose", dht.string, lambda o: o.deltaNeutralOpenClose),
            ("DeltaNeutralShortSale", dht.bool_, lambda o: o.deltaNeutralShortSale),
            ("DeltaNeutralShortSaleSlot", dht.int64, lambda o: o.deltaNeutralShortSaleSlot),
            ("DeltaNeutralDesignatedLocation", dht.string, lambda o: o.deltaNeutralDesignatedLocation),
            ("ContinuousUpdate", dht.bool_, lambda o: o.continuousUpdate),
            ("ReferencePriceType", dht.string, lambda o: map_values(o.referencePriceType, reference_price_type)),

            # COMBO ORDERS ONLY
            ("BasisPoints", dht.float64, lambda o: o.basisPoints),
            ("BasisPointsType", dht.int64, lambda o: o.basisPointsType),

            # SCALE ORDERS ONLY
            ("ScaleInitLevelSize", dht.int64, lambda o: o.scaleInitLevelSize),
            ("ScaleSubsLevelSize", dht.int64, lambda o: o.scaleSubsLevelSize),
            ("ScalePriceIncrement", dht.float64, lambda o: o.scalePriceIncrement),
            ("ScalePriceAdjustValue", dht.float64, lambda o: o.scalePriceAdjustValue),
            ("ScalePriceAdjustInterval", dht.int64, lambda o: o.scalePriceAdjustInterval),
            ("ScaleProfitOffset", dht.float64, lambda o: o.scaleProfitOffset),
            ("ScaleAutoReset", dht.bool_, lambda o: o.scaleAutoReset),
            ("ScaleInitPosition", dht.int64, lambda o: o.scaleInitPosition),
            ("ScaleInitFillQty", dht.int64, lambda o: o.scaleInitFillQty),
            ("ScaleRandomPercent", dht.bool_, lambda o: o.scaleRandomPercent),
            ("ScaleTable", dht.string, lambda o: o.scaleTable),

            # HEDGE ORDERS
            ("HedgeType", dht.string, lambda o: map_values(o.hedgeType, hedge_type)),
            ("HedgeParam", dht.string, lambda o: o.hedgeParam),

            # Clearing info
            ("Account", dht.string, lambda o: o.account),
            ("SettlingFirm", dht.string, lambda o: o.settlingFirm),
            ("ClearingAccount", dht.string, lambda o: o.clearingAccount),
            ("ClearingIntent", dht.string, lambda o: o.clearingIntent),

            # ALGO ORDERS ONLY
            ("AlgoStrategy", dht.string, lambda o: o.algoStrategy),

            ("AlgoParams", dht.stringset, lambda o: to_string_set(o.algoParams)),
            ("SmartComboRoutingParams", dht.stringset, lambda o: to_string_set(o.smartComboRoutingParams)),

            ("AlgoId", dht.string, lambda o: o.algoId),

            # What-if
            ("WhatIf", dht.bool_, lambda o: o.whatIf),

            # Not Held
            ("NotHeld", dht.bool_, lambda o: o.notHeld),
            ("Solicited", dht.bool_, lambda o: o.solicited),

            # models
            ("ModelCode", dht.string, lambda o: o.modelCode),

            # order combo legs

            ("OrderComboLegs", dht.stringset, lambda o: to_string_set(o.orderComboLegs)),

            ("OrderMiscOptions", dht.stringset, lambda o: to_string_set(o.orderMiscOptions)),

            # VER PEG2BENCH fields:
            ("ReferenceContractId", dht.int64, lambda o: o.referenceContractId),
            ("PeggedChangeAmount", dht.float64, lambda o: o.peggedChangeAmount),
            ("IsPeggedChangeAmountDecrease", dht.bool_, lambda o: o.isPeggedChangeAmountDecrease),
            ("ReferenceChangeAmount", dht.float64, lambda o: o.referenceChangeAmount),
            ("ReferenceExchangeId", dht.string, lambda o: o.referenceExchangeId),
            ("AdjustedOrderType", dht.string, lambda o: o.adjustedOrderType),

            ("TriggerPrice", dht.float64, lambda o: o.triggerPrice),
            ("AdjustedStopPrice", dht.float64, lambda o: o.adjustedStopPrice),
            ("AdjustedStopLimitPrice", dht.float64, lambda o: o.adjustedStopLimitPrice),
            ("AdjustedTrailingAmount", dht.float64, lambda o: o.adjustedTrailingAmount),
            ("AdjustableTrailingUnit", dht.int64, lambda o: o.adjustableTrailingUnit),
            ("LmtPriceOffset", dht.float64, lambda o: o.lmtPriceOffset),

            ("Conditions", dht.stringset, lambda o: to_string_set(o.conditions)),
            ("ConditionsCancelOrder", dht.bool_, lambda o: o.conditionsCancelOrder),
            ("ConditionsIgnoreRth", dht.bool_, lambda o: o.conditionsIgnoreRth),

            # ext operator
            ("ExtOperator", dht.string, lambda o: o.extOperator),

            # native cash quantity
            ("CashQty", dht.float64, lambda o: o.cashQty),

            ("Mifid2DecisionMaker", dht.string, lambda o: o.mifid2DecisionMaker),
            ("Mifid2DecisionAlgo", dht.string, lambda o: o.mifid2DecisionAlgo),
            ("Mifid2ExecutionTrader", dht.string, lambda o: o.mifid2ExecutionTrader),
            ("Mifid2ExecutionAlgo", dht.string, lambda o: o.mifid2ExecutionAlgo),

            ("DontUseAutoPriceForHedge", dht.bool_, lambda o: o.dontUseAutoPriceForHedge),

            ("IsOmsContainer", dht.bool_, lambda o: o.isOmsContainer),

            ("DiscretionaryUpToLimitPrice", dht.bool_, lambda o: o.discretionaryUpToLimitPrice),

            ("AutoCancelDate", dht.string, lambda o: o.autoCancelDate),
            ("FilledQuantity", dht.float64, lambda o: o.filledQuantity),
            ("RefFuturesConId", dht.int64, lambda o: o.refFuturesConId),
            ("AutoCancelParent", dht.bool_, lambda o: o.autoCancelParent),
            ("Shareholder", dht.string, lambda o: o.shareholder),
            ("ImbalanceOnly", dht.bool_, lambda o: o.imbalanceOnly),
            ("RouteMarketableToBbo", dht.bool_, lambda o: o.routeMarketableToBbo),
            ("ParentPermId", dht.int64, lambda o: o.parentPermId),

            ("UsePriceMgmtAlgo", dht.bool_, lambda o: o.usePriceMgmtAlgo),

            # soft dollars
            ("SoftDollarTier", dht.string, lambda o: to_string_val(o.softDollarTier)),
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbOrderStateLogger(IbComplexTypeLogger):
    """ Logging for IB OrderStates. """

    def __init__(self):
        column_details = [
            ("Status", dht.string, lambda os: os.status),

            ("InitMarginBefore", dht.string, lambda os: os.initMarginBefore),
            ("MaintMarginBefore", dht.string, lambda os: os.maintMarginBefore),
            ("EquityWithLoanBefore", dht.string, lambda os: os.equityWithLoanBefore),
            ("InitMarginChange", dht.string, lambda os: os.initMarginChange),
            ("MaintMarginChange", dht.string, lambda os: os.maintMarginChange),
            ("EquityWithLoanChange", dht.string, lambda os: os.equityWithLoanChange),
            ("InitMarginAfter", dht.string, lambda os: os.initMarginAfter),
            ("MaintMarginAfter", dht.string, lambda os: os.maintMarginAfter),
            ("EquityWithLoanAfter", dht.string, lambda os: os.equityWithLoanAfter),

            ("Commission", dht.float64, lambda os: os.commission),
            ("MinCommission", dht.float64, lambda os: os.minCommission),
            ("MaxCommission", dht.float64, lambda os: os.maxCommission),
            ("CommissionCurrency", dht.string, lambda os: os.commissionCurrency),
            ("WarningText", dht.string, lambda os: os.warningText),
            ("CompletedTime", dht.string, lambda os: os.completedTime),
            ("CompletedStatus", dht.string, lambda os: os.completedStatus),
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbTickAttribLogger(IbComplexTypeLogger):
    """ Logging for IB TickAttrib. """

    def __init__(self):
        column_details = [
            ("CanAutoExecute", dht.bool_, lambda ta: ta.canAutoExecute),
            ("PastLimit", dht.bool_, lambda ta: ta.pastLimit),
            ("PreOpen", dht.bool_, lambda ta: ta.preOpen),
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbBarDataLogger(IbComplexTypeLogger):
    """ Logging for IB BarData. """

    def __init__(self):
        column_details = [
            ("Timestamp", dht.datetime, lambda bd: unix_sec_to_dh_datetime(int(bd.date))),
            ("Open", dht.float64, lambda bd: bd.open),
            ("High", dht.float64, lambda bd: bd.high),
            ("Low", dht.float64, lambda bd: bd.low),
            ("Close", dht.float64, lambda bd: bd.close),
            ("Volume", dht.int64, lambda bd: bd.volume),
            ("BarCount", dht.int64, lambda bd: bd.barCount),
            ("Average", dht.float64, lambda bd: bd.average),
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbHistoricalTickLastLogger(IbComplexTypeLogger):
    """Logging for HistoricalTickLast."""

    def __init__(self):
        column_details = [
            ("Timestamp", dht.datetime, lambda t: unix_sec_to_dh_datetime(t.time)),
            ("Price", dht.float64, lambda t: t.price),
            ("Size", dht.int64, lambda t: t.size),
            ("PastLimit", dht.bool_, lambda t: t.tickAttribLast.pastLimit),
            ("Unreported", dht.bool_, lambda t: t.tickAttribLast.unreported),
            ("Exchange", dht.string, lambda t: t.exchange),
            ("SpecialConditions", dht.string, lambda t: t.specialConditions)
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbHistoricalTickBidAskLogger(IbComplexTypeLogger):
    """Logging for HistoricalTickBidAsk."""

    def __init__(self):
        column_details = [
            ("Timestamp", dht.datetime, lambda t: unix_sec_to_dh_datetime(t.time)),
            ("BidPrice", dht.float64, lambda t: t.priceBid),
            ("AskPrice", dht.float64, lambda t: t.priceAsk),
            ("BidSize", dht.int64, lambda t: t.sizeBid),
            ("AskSize", dht.int64, lambda t: t.sizeAsk),
            ("BidPastLow", dht.bool_, lambda t: t.tickAttribBidAsk.bidPastLow),
            ("AskPastHigh", dht.bool_, lambda t: t.tickAttribBidAsk.askPastHigh),
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbFamilyCodeLogger(IbComplexTypeLogger):
    """Logging for FamilyCode."""

    def __init__(self):
        column_details = [
            ("AccountID", dht.string, lambda fc: fc.accountID),
            ("FamilyCode", dht.string, lambda fc: fc.familyCodeStr),
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbPriceIncrementLogger(IbComplexTypeLogger):
    """Logging for PriceIncrement."""

    def __init__(self):
        column_details = [
            ("LowEdge", dht.float64, lambda pi: pi.lowEdge),
            ("Increment", dht.float64, lambda pi: pi.increment),
        ]

        IbComplexTypeLogger.__init__(self, column_details)


class IbContractDetailsLogger(IbComplexTypeLogger):
    """Logging for ContractDetails."""

    def __init__(self):
        contract_details = [
            (** * contractstuff ** * cd.contract),
            ("MarketName", dht.string, lambda cd: cd.marketName),
            ("MinTick", dht.float64, lambda cd: cd.minTick),
            ("OrderTypes", dht.string, lambda cd: cd.orderTypes),
            ("ValidExchanges", dht.string, lambda cd: cd.validExchanges),
            ("PriceMagnifier", dht.int64, lambda cd: cd.priceMagnifier),
            ("UnderConId", dht.int64, lambda cd: cd.underConId),
            ("LongName", dht.string, lambda cd: cd.longName),
            ("ContractMonth", dht.string, lambda cd: cd.contractMonth),
            ("Industry", dht.string, lambda cd: cd.industry),
            ("Category", dht.string, lambda cd: cd.category),
            ("SubCategory", dht.string, lambda cd: cd.subcategory),
            ("TimeZoneId", dht.string, lambda cd: cd.timeZoneId),
            ("TradingHours", dht.string, lambda cd: cd.tradingHours),
            ("LiquidHours", dht.string, lambda cd: cd.liquidHours),
            ("EvRule", dht.string, lambda cd: cd.evRule),
            ("EvMultiplier", dht.int64, lambda cd: cd.evMultiplier),
            ("MdSizeMultiplier", dht.int64, lambda cd: cd.mdSizeMultiplier),
            ("AggGroup", dht.int64, lambda cd: cd.aggGroup),  # TODO: map?
            ("UnderSymbol", dht.string, lambda cd: cd.underSymbol),
            ("UnderSecType", dht.string, lambda cd: cd.underSecType),
            ("MarketRuleIds", dht.string, lambda cd: cd.marketRuleIds),
            ("SecIdList", dht.stringset, lambda cd: to_string_set(cd.secIdList)),  # TODO: right type?
            ("RealExpirationDate", dht.string, lambda cd: cd.realExpirationDate),
            ("LastTradeTime", dht.string, lambda cd: cd.lastTradeTime),
            ("StockType", dht.string, lambda cd: cd.stockType),
            # BOND values
            ("CUSIP", dht.string, lambda cd: cd.cusip),
            ("Ratings", dht.string, lambda cd: cd.ratings),
            ("DescAppend", dht.string, lambda cd: cd.descAppend),
            ("BondType", dht.string, lambda cd: cd.bondType),
            ("CouponType", dht.string, lambda cd: cd.couponType),
            ("Callable", dht.bool_, lambda cd: cd.callable),
            ("Putable", dht.bool_, lambda cd: cd.putable),
            ("Coupon", dht.int64, lambda cd: cd.coupon),
            ("Convertible", dht.bool_, lambda cd: cd.convertible),
            ("Maturity", dht.string, lambda cd: cd.maturity),  # TODO: convert date time?
            ("IssueDate", dht.string, lambda cd: cd.issueDate),  # TODO: convert date time?
            ("NextOptionDate", dht.string, lambda cd: cd.nextOptionDate),  # TODO: convert date time?
            ("NextOptionType", dht.string, lambda cd: cd.nextOptionType),
            ("NextOptionPartial", dht.bool_, lambda cd: cd.nextOptionPartial),
            ("Notes", dht.string, lambda cd: cd.notes),
        ]

        IbComplexTypeLogger.__init__(self, contract_details)

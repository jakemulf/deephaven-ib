from typing import Any, List, Tuple

import jpy
from deephaven import Types as dht

ArrayStringSet = jpy.get_type("io.deephaven.stringset.ArrayStringSet")


def _map_values(value, map, default=lambda v: f"UNKNOWN(v)"):
    """ Maps one set of values to another.  A default value is used if the value is not in the map. """

    if value is None:
        return None

    try:
        return map[value]
    except KeyError:
        # TODO: log bad mapping
        return default(value)


def _to_string_val(value):
    """ Converts a value to a string. """

    if value is None:
        return None

    return str(value)


def _to_string_set(value):
    """ Converts an iterable to a string set. """

    if value is None:
        return None

    return ArrayStringSet(",".join([_to_string_val(v) for v in value]))


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


class IbOrderLogger(IbComplexTypeLogger):
    """ Class for logging IB Orders. """
    
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
            ("OcaType", dht.string, lambda o: _map_values(o.ocaType, oca_types)),
            ("OrderRef", dht.string, lambda o: o.orderRef),
            ("Transmit", dht.bool_, lambda o: o.transmit),
            ("ParentId", dht.int64, lambda o: o.parentId),
            ("BlockOrder", dht.bool_, lambda o: o.blockOrder),
            ("SweepToFill", dht.bool_, lambda o: o.sweepToFill),
            ("DisplaySize", dht.int64, lambda o: o.displaySize),
            ("TriggerMethod", dht.string, lambda o: _map_values(o.triggerMethod, trigger_methods)),
            ("OutsideRth", dht.bool_, lambda o: o.outsideRth),
            ("Hidden", dht.bool_, lambda o: o.hidden),
            ("GoodAfterTime", dht.string, lambda o: o.goodAfterTime),
            ("GoodTillDate", dht.string, lambda o: o.goodTillDate),
            ("Rule80A", dht.string, lambda o: _map_values(o.rule80A, rule80_values)),
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
            ("OpenClose", dht.string, lambda o: _map_values(o.openClose, open_close_values)),
            ("Origin", dht.string, lambda o: _map_values(o.origin, origin_values)),
            ("ShortSaleSlot", dht.string, lambda o: _map_values(o.shortSaleSlot, short_sale_slot_values)),
            ("ExemptClode", dht.int64, lambda o: o.exemptCode),

            # SMART routing only
            ("DiscretionaryAmt", dht.int64, lambda o: o.discretionaryAmt),
            ("ETradeOnly", dht.bool_, lambda o: o.eTradeOnly),
            ("FirmQuoteOnly", dht.bool_, lambda o: o.firmQuoteOnly),
            ("NbboPriceCap", dht.float64, lambda o: o.nbboPriceCap),
            ("OptOutSmarRouting", dht.bool_, lambda o: o.optOutSmartRouting),

            # BOX exchange orders only
            ("AuctionStrategy", dht.string, lambda o: _map_values(o.auctionStrategy, auction_stragey_values)),
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
            ("VolatilityType", dht.string, lambda o: _map_values(o.volatilityType, volatility_type)),
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
            ("ReferencePriceType", dht.string, lambda o: _map_values(o.referencePriceType, reference_price_type)),

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
            ("HedgeType", dht.string, lambda o: _map_values(o.hedgeType, hedge_type)),
            ("HedgeParam", dht.string, lambda o: o.hedgeParam),

            # Clearing info
            ("Account", dht.string, lambda o: o.account),
            ("SettlingFirm", dht.string, lambda o: o.settlingFirm),
            ("ClearingAccount", dht.string, lambda o: o.clearingAccount),
            ("ClearingIntent", dht.string, lambda o: o.clearingIntent),

            # ALGO ORDERS ONLY
            ("AlgoStrategy", dht.string, lambda o: o.algoStrategy),

            ("AlgoParams", dht.stringset, lambda o: _to_string_set(o.algoParams)),
            ("SmartComboRoutingParams", dht.stringset, lambda o: _to_string_set(o.smartComboRoutingParams)),

            ("AlgoId", dht.string, lambda o: o.algoId),

            # What-if
            ("WhatIf", dht.bool_, lambda o: o.whatIf),

            # Not Held
            ("NotHeld", dht.bool_, lambda o: o.notHeld),
            ("Solicited", dht.bool_, lambda o: o.solicited),

            # models
            ("ModelCode", dht.string, lambda o: o.modelCode),

            # order combo legs

            ("OrderComboLegs", dht.stringset, lambda o: _to_string_set(o.orderComboLegs)),

            ("OrderMiscOptions", dht.stringset, lambda o: _to_string_set(o.orderMiscOptions)),

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

            ("Conditions", dht.stringset, lambda o: _to_string_set(o.conditions)),
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

            ("Don'tUseAutoPriceForHedge", dht.bool_, lambda o: o.dontUseAutoPriceForHedge),

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
            ("SoftDollarTier", dht.string, lambda o: _to_string_val(o.softDollarTier)),
        ]

        IbComplexTypeLogger.__init__(column_details)
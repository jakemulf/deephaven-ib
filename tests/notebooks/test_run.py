from ibapi.contract import Contract

import deephaven_ib as dhib

client = dhib.IbSessionTws(download_short_rates=False)

print(f"IsConnected: {client.is_connected()}")

client.connect(host="host.docker.internal", port=7496)

print(f"IsConnected: {client.is_connected()}")

for k, v in client.tables.items():
    globals()[k] = v

# c = Contract()
# c.secType = "STK"
# c.exchange = "NASDAQ"
# c.symbol = "AAPL"
#
# rc = client.get_registered_contract(c)

c = Contract()
c.symbol = 'AAPL'
c.secType = 'STK'
c.exchange = 'SMART'
c.currency = 'USD'

rc = client.get_registered_contract(c)
print(rc)

client.set_market_data_type(dhib.MarketDataType.DELAYED)
client.request_market_data(rc)
client.request_tick_data_realtime(rc, dhib.TickDataType.BID_ASK)
client.request_tick_data_realtime(rc, dhib.TickDataType.LAST)
client.request_tick_data_realtime(rc, dhib.TickDataType.MIDPOINT)


def special_guy(a, b, c) -> Callable:
    return lambda x: x + a + b + c
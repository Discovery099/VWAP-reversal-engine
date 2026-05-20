# Pine Manual QA Checklist

TradingView compilation must be performed manually because the local environment cannot compile Pine.

- [ ] Script compiles as Pine Script v6.
- [ ] VWAP resets at the daily session boundary on the selected chart.
- [ ] Absorption marker appears only on confirmed bars.
- [ ] Volume percentile and displacement/ATR approximately match Python on an exported sample window.
- [ ] Above/below/near VWAP labels are correct.
- [ ] Near-VWAP events do not produce directional trades unless explicitly allowed by future configuration.
- [ ] Strategy mode can be disabled; alerts still work without paper orders.
- [ ] Debug table shows volume percentile, displacement/ATR, VWAP distance/ATR, location, and block reason.
- [ ] No live execution, webhook order routing, or broker API behavior is present.

# ================= LANGUAGE PLAYBOOK (LONG + SHORT) =================
# One entry per market situation. Each has a prediction + prescription for BOTH directions.
# {placeholders} are filled with the coin's own numbers.
SITUATIONS = {
"PUMP_MOMENTUM": {
  "label": "Pump with momentum", "icon": "🚀",
  "when": "Pumped within the last 6h, not yet overbought, and this coin's past pumps usually continued.",
  "long_prediction": "{sym} pumped {last_pump} about {hrs_pump}h ago. After {post_pump_n} similar pumps in the last 6 months, the next 4h averaged {post_pump_avg} and was positive {post_pump_win} of the time. Momentum is likely to continue over the next 1-4 hours.",
  "long_prescription": "Long bias while price holds above the pump's midpoint. Prefer small pullbacks over chasing green candles. Step aside if volume fades or RSI ({rsi}) goes above 80.",
  "short_prediction": "Shorting {sym} into a pump that has historically continued ({post_pump_win} positive over 4h) carries high squeeze risk.",
  "short_prescription": "No short. Wait for momentum to fade: falling volume, RSI above 80, or a lower high."},
"OVEREXTENDED": {
  "label": "Overextended / exhaustion", "icon": "🔥",
  "when": "Overbought (RSI >= 78 or >= 3 std-devs above the 7d mean), usually after a pump that historically did not continue.",
  "long_prediction": "{sym} is {ret_24h} in 24h with RSI {rsi}, {z7} std-devs from its 7-day mean. Chasing here has poor odds.",
  "long_prescription": "No long. Wait for a pullback toward the 7-day mean or RSI back below 60 before reconsidering.",
  "short_prediction": "{sym} looks stretched: {ret_24h} in 24h, RSI {rsi}, {z7} std-devs from its 7-day mean. Past pumps on this coin: next 4h averaged {post_pump_avg} and was negative {post_pump_dn} of the time (n={post_pump_n}). A pullback is likely over the next hours.",
  "short_prescription": "Fade candidate. Wait for the first sign of exhaustion (a lower high, or a red candle on rising volume) instead of shorting a still-accelerating move. Invalid if price makes a new high on strong volume."},
"FALLING_KNIFE": {
  "label": "Heavy dump, no recovery", "icon": "🔪",
  "when": "30d drawdown of 30%+, still printing lower lows, under 25% of the 30d range recovered.",
  "long_prediction": "{sym} is {dd30} from its 30-day high and still making lower lows. It has recovered only {rec} of its 30-day range. No recovery structure yet.",
  "long_prescription": "No long. Wait for higher lows, falling sell volume and RSI turning up from below 30.",
  "short_prediction": "Downside momentum on {sym} is intact: {dd30} from the 30-day high, lower lows, only {rec} recovered. Continuation is likely, but after a drop this deep a sharp relief bounce is also a real risk.",
  "short_prescription": "Continuation-short only on weak bounces that fail below the broken level. Do not chase the low: with RSI {rsi}, a squeeze can be violent."},
"STILL_DUMPING": {
  "label": "Dumping right now", "icon": "📉",
  "when": "A dump event in the last 24h and price is still making new lows.",
  "long_prediction": "{sym} dumped {last_dump} about {hrs_dump}h ago and is still printing new lows. After {post_dump_n} past dumps, the next 4h averaged {post_dump_avg}.",
  "long_prescription": "Stay out. Re-check once price stops making new lows for several candles.",
  "short_prediction": "{sym} dumped {last_dump} about {hrs_dump}h ago and keeps making new lows. After {post_dump_n} past dumps the next 4h was negative {post_dump_dn} of the time (avg {post_dump_avg}). More downside is likely over the next few hours.",
  "short_prescription": "Short bias while it keeps making lower lows. Prefer entries on small bounces. Step aside if price stops making new lows or RSI ({rsi}) drops below 25."},
"DUMP_STABILIZING": {
  "label": "Dump stabilizing (rebound watch)", "icon": "🩹",
  "when": "Deep drawdown or recent dump, RSI <= 42, no new lows, small bounce off the low.",
  "long_prediction": "{sym} is {dd30} below its 30-day high (RSI {rsi}) and has stopped making new lows. After {post_dump_n} past dumps, the next 4h was positive {post_dump_win} of the time (avg {post_dump_avg}). A relief bounce is likely over the next few hours.",
  "long_prescription": "Rebound watch for a long. Confirmation = a close above the recent 4h high. Invalid if the recent low breaks; the bigger trend is still down.",
  "short_prediction": "{sym} has stopped making new lows after a deep drop (RSI {rsi}). Shorting here is late and exposed to a relief bounce: past dumps were positive {post_dump_win} of the time over 4h.",
  "short_prescription": "No short. Wait for the bounce to fail at resistance before reconsidering."},
"UPTREND_PULLBACK": {
  "label": "Dip inside an uptrend", "icon": "📈",
  "when": "7d linear-regression trend is up (R2 >= 0.5) and price is below its 7d mean.",
  "long_prediction": "{sym} is in a steady uptrend ({trend7} per day, R2 {r2}) and sits {z7} std-devs from its 7-day mean. Dips in this trend tend to be bought; a move back toward the trend line is likely.",
  "long_prescription": "Long bias on the dip while price stays near the trend line. A close well below the line breaks the trend and cancels the idea.",
  "short_prediction": "{sym} is in an uptrend ({trend7} per day, R2 {r2}). A dip inside it is more likely to be bought than to turn into a breakdown.",
  "short_prescription": "No short while the trend line holds. A decisive close below it would change this."},
"DOWNTREND": {
  "label": "Established downtrend", "icon": "⬇️",
  "when": "7d linear-regression trend is down (R2 >= 0.5), price not stretched above its mean.",
  "long_prediction": "{sym} is trending down ({trend7} per day, R2 {r2}). Bounces inside this trend have been weak.",
  "long_prescription": "No long until the trend slope flattens or turns up.",
  "short_prediction": "{sym} is in a steady downtrend ({trend7} per day, R2 {r2}). Continuation over the coming hours is more likely than a reversal.",
  "short_prescription": "Short bias with the trend. Best entries are on bounces toward the trend line. Invalid if price closes above it."},
"DOWNTREND_BOUNCE": {
  "label": "Bounce inside a downtrend", "icon": "↩️",
  "when": "Downtrend (R2 >= 0.5) but price has bounced >= 0.8 std-devs above its 7d mean.",
  "long_prediction": "{sym} is bouncing ({z7} std-devs vs its 7d mean) inside a downtrend ({trend7} per day, R2 {r2}). Bounces like this rarely become reversals.",
  "long_prescription": "No long. Treat the bounce as a trap until the trend slope turns.",
  "short_prediction": "{sym} is in a downtrend ({trend7} per day, R2 {r2}) and has bounced to {z7} std-devs vs its 7-day mean. A rejection and resumption of the decline is likely.",
  "short_prescription": "Short-the-bounce candidate near the trend line. Invalid on a close above it or a new 7-day high."},
"PATTERN_BULLISH": {
  "label": "Bullish pattern match", "icon": "🧬",
  "when": "The last 24h closely match past setups that went up more often than the coin's base rate.",
  "long_prediction": "The last 24h of {sym} price action match {n_an} historical setups. In {p_up4} of them price was higher 4h later (median {med4}, middle range {q25} to {q75}), versus a {base4} base rate.",
  "long_prescription": "Mild long bias. A statistical edge, not a certainty. Wait for price to hold above the last hour's low.",
  "short_prediction": "Pattern matching on {sym} leans up ({p_up4} up vs {p_dn4} down in similar setups). A short has no statistical edge.",
  "short_prescription": "No short."},
"PATTERN_BEARISH": {
  "label": "Bearish pattern match", "icon": "🧬",
  "when": "The last 24h closely match past setups that went down more often than the coin's base rate.",
  "long_prediction": "Similar setups on {sym} fell more often than they rose over 4h ({p_dn4} down vs {p_up4} up). No statistical edge for a long.",
  "long_prescription": "No long.",
  "short_prediction": "The last 24h of {sym} price action match {n_an} historical setups. In {p_dn4} of them price was lower 4h later (median {med4}, middle range {q25} to {q75}), versus a {base_dn4} base rate.",
  "short_prescription": "Mild short bias. A statistical edge, not a certainty. Wait for price to lose the last hour's low."},
"NO_EDGE": {
  "label": "No statistical edge", "icon": "😐",
  "when": "Nothing stands out in either direction.",
  "long_prediction": "{sym} shows no clear edge either way: similar setups went up {p_up4} / down {p_dn4} of the time (base rates {base4} / {base_dn4}), trend R2 {r2}.",
  "long_prescription": "Nothing to do. Keep it on the radar.",
  "short_prediction": "{sym} shows no clear edge either way: similar setups went up {p_up4} / down {p_dn4} of the time (base rates {base4} / {base_dn4}), trend R2 {r2}.",
  "short_prescription": "Nothing to do. Keep it on the radar."},
}
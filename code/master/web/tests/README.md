# Web frontend UI tests

Browser-driven regression tests for the channels UI, run with **pytest +
Playwright** against a throwaway Django live server. They exercise the real
compiled JavaScript in a headless Chromium, so they catch bugs that pure Python
tests can't (DOM wiring, click handlers, the channel-selection logic).

## One-time setup

From this directory's project root (`code/master/web/`):

```bash
source ../env_tethys/bin/activate
pip install -r requirements-dev.txt
playwright install --with-deps chromium   # downloads Chromium + apt libs (needs sudo)
```

## Running

```bash
cd code/master/web
pytest
```

`conftest.py` compiles `static/ts` → `static/js` first (the compiled JS is no
longer committed — it's rebuilt on deploy), so the tests always run against the
current TypeScript.

## What's covered

- `test_channels_ui.py` — **regression for the sparse-channel settings crash.**
  Channels are identified by number and may be non-contiguous (e.g. 1, 2, 5).
  The settings code once looked a channel up with `channels[number - 1]`,
  assuming a dense array, so clicking channel 5 evaluated `channels[4]` on a
  3-element array and threw `TypeError: undefined is not an object`. The test
  injects channels 1/2/5 through the page's own render path, clicks channel 5,
  and asserts the settings panel opens with the right title and that no uncaught
  error fired.

## How it works

- A test-only settings module, `tethys_web.settings_test`, points the staticfiles
  finders at the in-repo `static/` tree so the live server serves the freshly
  compiled JS without a `collectstatic` step.
- The channels view needs no database and the page gets its data over a
  websocket, so the test bypasses both: it calls `tethys.channel.updateDataSet()`
  directly to seed the exact channel set, making the test deterministic and free
  of any real device/API/DB state.

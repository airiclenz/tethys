# Initial installation

For installing Tehys the first time, you need to install git:

`sudo app install git -y`

Then you can download the code with:

`git clone https://github.com/airiclenz/tethys.git tethys`

Change into the installation directory:

`cd tethys/code/master/install/`

...and start the installation:

`./install.sh`

The installer generates a local API key and prints it (it is also stored in the
git-ignored `code/master/globals/secrets.py`). The API requires this key on every
mutating request — including manually activating/deactivating pumps. Open the web
UI, go to **Settings** (top menu), paste the key, and Save. Read-only views work
without it.


# API key

The shared API key lives in `code/master/globals/secrets.py` (git-ignored, never
committed). A template is provided in `secrets.example.py`. To create or rotate it
manually:

```
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put the value in `secrets.py` as `TETHYS_API_KEY = "..."`, restart the services
(`./services-restart.sh`), and update the key in the web UI Settings. The core
process reads the same file, so no other change is needed.


# Update the Services

If you want to update the installed services from the code, you can run the script

`installServices.sh`

..in the same installation folder `tethys/code/master/install/`

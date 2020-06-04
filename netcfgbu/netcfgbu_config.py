import sys
from os.path import expandvars
from pathlib import Path
import toml
from itertools import chain

from .logger import setup_logging, get_logger


def load(*, filepath=None, fileio=None):

    if filepath:
        app_cfg_file = Path(filepath)
        fileio = app_cfg_file.open()

    app_cfg = toml.load(fileio)

    setup_logging(app_cfg)

    app_defaults = app_cfg["defaults"]
    for var_name, var_value in app_defaults.items():
        if isinstance(var_value, str):
            app_defaults[var_name] = expandvars(var_value)

    load_creds(app_cfg)

    configs_dir = Path(app_defaults["configs_dir"])
    if not configs_dir.is_dir():
        configs_dir.mkdir()

    return app_cfg


def load_creds(app_cfg):
    log = get_logger()

    creds = list()

    # default credentials

    creds.append((app_cfg["defaults"]["credentials"],))

    # global credentials [optional]

    if gl_creds := app_cfg.get("credentials"):
        creds.append(gl_creds)

    # per os_name credentials

    os_creds_list = set()
    for os_name, os_spec in app_cfg.get("os_name").items():
        if os_creds := os_spec.get("credentials"):
            os_creds_list.add(os_name)
            creds.append(os_creds)

    # expand the used environment variables; checking to see if any are used
    # that are defined in the Users in the environment.

    for cred in chain.from_iterable(creds):
        for key, value in cred.items():
            new_value = cred[key] = expandvars(value)
            if new_value.startswith("$") and new_value == value:
                msg = f'credential {cred["username"]} using undefined variable "{value}", aborting.'
                sys.exit(msg)
                # cred.clear()
                # break

    # now remove any credentials that did not expand correctly.

    if gl_creds:
        app_cfg["credentials"] = list(filter(None, gl_creds))

    for os_name in os_creds_list:
        app_cfg["os_name"][os_name]["credentials"] = list(
            filter(None, app_cfg["os_name"][os_name]["credentials"])
        )

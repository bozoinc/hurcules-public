"""TDD tests for the license-compliance gate (deterministic, no network)."""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.license_gate import check_license, detect_license

MIT = """MIT License
Copyright (c) 2024 Someone
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software")...
"""

APACHE = """Apache License
Version 2.0, January 2004
This is the Apache License text.
"""

BSD3 = """Copyright (c) 2024 Someone. All rights reserved.
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
... neither the name of the copyright holder nor the names of its
contributors may be used to endorse or promote products derived from this
software without specific prior written permission.
"""

BSD2 = """Copyright (c) 2024 Someone. All rights reserved.
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
...
"""

GPL3 = """GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007
Everyone is permitted to copy and distribute verbatim copies of this license
document, but changing it is not allowed.
"""

GPL2 = """GNU GENERAL PUBLIC LICENSE
Version 2, June 1991
Everyone is permitted to copy and distribute verbatim copies of this license
document, but changing it is not allowed.
"""

LGPL = """GNU LESSER GENERAL PUBLIC LICENSE
Version 3, 29 June 2007
"""

PROPRIETARY = """Copyright (c) 2024 MegaCorp. All rights reserved.
This software is proprietary. No license granted to any third party.
Personal use only.
"""

UNKNOWN = """This file contains some legal-ish words but nothing recognizable."""


def write(repo, name, content):
    (repo / name).write_text(content)
    return repo


def test_mit_detected_permissive(tmp_path):
    det = detect_license(write(tmp_path, "LICENSE", MIT))
    assert det["status"] == "permissive"
    assert det["license_name"] == "MIT"
    assert det["file"] == "LICENSE"


def test_apache_detected_permissive(tmp_path):
    det = detect_license(write(tmp_path, "LICENSE", APACHE))
    assert det["status"] == "permissive"
    assert det["license_name"] == "Apache-2.0"


def test_bsd3_vs_bsd2(tmp_path):
    assert detect_license(write(tmp_path, "LICENSE", BSD3))["license_name"] == "BSD-3-Clause"
    repo2 = tmp_path / "bsd2repo"
    repo2.mkdir()
    assert detect_license(write(repo2, "LICENSE", BSD2))["license_name"] == "BSD-2-Clause"


def test_gpl3_copyleft_with_warning(tmp_path):
    det = detect_license(write(tmp_path, "COPYING", GPL3))
    assert det["status"] == "copyleft"
    assert det["license_name"] == "GPL-3.0"
    chk = check_license(tmp_path)
    assert chk["ok"] is True
    assert chk["copyleft"] is True


def test_gpl2_version_disambiguated(tmp_path):
    det = detect_license(write(tmp_path, "LICENSE", GPL2))
    assert det["status"] == "copyleft"
    assert det["license_name"] == "GPL-2.0"


def test_lgpl_copyleft(tmp_path):
    det = detect_license(write(tmp_path, "LICENSE", LGPL))
    assert det["status"] == "copyleft"
    assert det["license_name"] == "LGPL"


def test_proprietary_blocked_always(tmp_path):
    det = detect_license(write(tmp_path, "LICENSE", PROPRIETARY))
    assert det["status"] == "proprietary"
    for marketplace in (False, True):
        chk = check_license(tmp_path, marketplace=marketplace)
        assert chk["ok"] is False
        assert chk["blocked_reason"] == "non-compliant license"


def test_no_license_none_allowed_when_not_marketplace(tmp_path):
    det = detect_license(tmp_path)
    assert det["status"] == "none"
    assert det["file"] is None
    chk = check_license(tmp_path, marketplace=False)
    assert chk["ok"] is True
    assert chk["blocked_reason"] is None


def test_no_license_blocked_when_marketplace(tmp_path):
    chk = check_license(tmp_path, marketplace=True)
    assert chk["ok"] is False
    assert chk["blocked_reason"] == "no license — cannot distribute"


def test_unknown_file_blocked_always(tmp_path):
    det = detect_license(write(tmp_path, "LICENSE", UNKNOWN))
    assert det["status"] == "unknown"
    assert det["license_name"] is None
    chk = check_license(tmp_path)
    assert chk["ok"] is False
    assert chk["blocked_reason"] == "non-compliant license"


def test_mit_body_beats_all_rights_reserved(tmp_path):
    # "All rights reserved" header must not flip a real MIT body to proprietary.
    text = "Copyright (c) 2024 Someone. All rights reserved.\n" + MIT
    det = detect_license(write(tmp_path, "LICENSE", text))
    assert det["status"] == "permissive"
    assert det["license_name"] == "MIT"


def test_case_insensitive_and_variant_filenames(tmp_path):
    write(tmp_path, "LICENSE-MIT", MIT)
    det = detect_license(tmp_path)
    assert det["status"] == "permissive"
    write(tmp_path, "license.txt", APACHE)
    assert detect_license(tmp_path)["status"] == "permissive"


def test_deterministic(tmp_path):
    repo = write(tmp_path, "LICENSE", MIT)
    first = detect_license(repo)
    second = detect_license(repo)
    assert first == second


def test_not_a_directory_raises(tmp_path):
    with pytest.raises(ValueError):
        detect_license(str(tmp_path / "missing"))
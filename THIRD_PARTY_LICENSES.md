# Third-party licenses

This project is released under the [MIT License](LICENSE). It includes or builds on the third-party work below, which
keeps its own license. This file lists what is **copied into this repository**, and, for information, the main
components that are installed or pulled at build time and are not part of this repository.

## 1. Included in this repository

### Fonts (SIL Open Font License 1.1)

Self-hosted as `.woff2` subsets in `api/app/static/fonts/` (the admin) and bundled at build time from the
`@fontsource` packages (the public site):

| Font | Copyright | Source |
|---|---|---|
| **Poppins** | Copyright 2020 The Poppins Project Authors | https://github.com/itfoundry/Poppins |
| **IBM Plex Sans Thai** | Copyright 2019 IBM Corp. All rights reserved. | https://github.com/IBM/plex |
| **JetBrains Mono** | Copyright 2020 The JetBrains Mono Project Authors | https://github.com/JetBrains/JetBrainsMono |

The fonts are used unmodified apart from being cut into language subsets and converted to WOFF2 by the Fontsource
project. They are licensed under the SIL Open Font License, Version 1.1, reproduced in full in
[section 3](#3-sil-open-font-license-version-11).

### htmx

`api/app/static/htmx.min.js` is [htmx](https://htmx.org) 2.0.4, copyright Big Sky Software, distributed under the
Zero-Clause BSD license (0BSD), which does not require attribution. It is listed here for completeness.

### Tailwind CSS and daisyUI (in the generated admin stylesheet)

`api/app/static/admin.css` is generated from `api/css/input.css` and the admin templates by the Tailwind standalone CLI
with the daisyUI plugin. The output contains parts of both projects, which are MIT licensed:

- **Tailwind CSS** 4.3.3, Copyright (c) Tailwind Labs, Inc. https://tailwindcss.com (the notice is kept in the first
  line of `admin.css`).
- **daisyUI** 5.7.50, Copyright (c) 2020 Pouya Saadeghi. https://daisyui.com

The MIT License requires that "the above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software"; the full MIT text in [LICENSE](LICENSE) applies to these projects in the same words.
Their own license files are in their repositories: https://github.com/tailwindlabs/tailwindcss and
https://github.com/saadeghi/daisyui.

## 2. Not included in this repository (installed when you build or run it)

For information only. Each is obtained from its package registry or image registry under its own license, and the
authoritative license text is the one shipped with that package or image.

| Component | License |
|---|---|
| Next.js, React, react-markdown, Tailwind CSS (npm) | MIT |
| FastAPI, SQLAlchemy, Pydantic, Alembic, argon2-cffi, pyotp | MIT |
| Uvicorn, Jinja2, httpx | BSD-3-Clause |
| boto3, asyncpg, PyThaiNLP | Apache-2.0 |
| Pillow | MIT-CMU (HPND) |
| PostgreSQL, pgvector | PostgreSQL License |
| Caddy, RustFS | Apache-2.0 |
| Uptime Kuma (optional monitor) | MIT |

The question assistant calls the **Google Gemini API**, a service governed by Google's own terms, not a library.

## 3. SIL Open Font License, Version 1.1

Applies to Poppins, IBM Plex Sans Thai and JetBrains Mono (see section 1). The license text is reproduced from the
Fontsource packages that distribute these fonts.

```text
This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
http://scripts.sil.org/OFL


-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
```

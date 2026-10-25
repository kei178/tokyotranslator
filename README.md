# tokyotranslator.com

Static rebuild of **Tokyo Translator**, the one-page portfolio site of Nadine Quade,
a freelance translator (English / Japanese → German, MTPE, German proofreading).

The site used to run on WordPress on a Sakura Internet server. Because of the
ongoing stream of PHP/WordPress vulnerabilities, the WordPress install has been
shut down. This repository rebuilds the same content as plain static HTML and
hosts it on GitHub Pages, with the DNS zone (and the Zoho mail records in it)
left untouched at Sakura.

Status (2026-10-25): the static site in [`site/`](site/) is live at
<https://tokyotranslator.com/> on GitHub Pages. The three captured WordPress
pages in [`reference/`](reference/) are the source the rebuild was made from.

## Documents

| Document | Purpose |
|---|---|
| [docs/superpowers/specs/2026-10-22-static-site-migration-design.md](docs/superpowers/specs/2026-10-22-static-site-migration-design.md) | Architecture decisions and the reasoning behind them |
| [docs/superpowers/plans/2026-10-22-static-site-migration.md](docs/superpowers/plans/2026-10-22-static-site-migration.md) | Step-by-step implementation plan |
| [reference/](reference/) | Saved HTML of the old WordPress pages (`de.html`, `en.html`, `ja.html`) |

## What the site is

A single landing page, available in three languages, with these sections:

| Section | German (default) | English | Japanese |
|---|---|---|---|
| Hero taglines | Fachübersetzungen / Literaturübersetzungen / Korrektorat | Specialist translations / Book translation / Proofreading | 専門文書の翻訳 / 書籍翻訳 / プルーフリーディング |
| Profile | Mein Profil | My Profile | プロフィール |
| Services | Leistungen | Services | サービス |
| Rates | Preise | Rates | 料金 |
| Legal notice | Impressum | Impressum | 管理者情報 |
| Contact | Kontakt (E-Mail) | Contact (email) | お問い合わせ（メール） |
| Privacy | Datenschutz | Privacy | プライバシーポリシー |

The contact form is dropped in the static version. Contact is by email
(`quade@tokyotranslator.com`) instead.

### URL scheme (kept from the old site)

| URL | Language |
|---|---|
| `/` | German (`de`) – the default |
| `/en/` | English |
| `/ja/` | Japanese |

Each page links to the other two languages; switching language is a normal
page navigation, no JavaScript involved.

## Old stack (for reference)

- WordPress 5.3.26, theme **Graphy** (Themegraphy), plugins **Bogo** (languages),
  **Contact Form 7**, **Smart Slider 3** (hero slider).
- Fonts: Lora (body), Montserrat (headings), loaded from Google Fonts.
- Images: three hero slides (`tokyotranslator_slider{1,2,3}-1.jpg`, 2017) and one
  profile photo (`profile_nq.jpg`, 2020). Recovered from the Wayback Machine and
  stored, resized and EXIF-stripped, in `site/assets/img/`.
- Server: Sakura Internet (`153.126.130.234`), now unreachable.

## Domain and DNS (current state, 2026-10-25)

| Record | Value |
|---|---|
| Registrar | JPRS, via Sakura Internet's domain service. **Registration expires 2026-11-30 – renew at Sakura.** |
| Nameservers | `ns1.dns.ne.jp`, `ns2.dns.ne.jp` (Sakura Internet) – unchanged |
| `A tokyotranslator.com` | `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` (GitHub Pages) |
| `CNAME www` | `kei178.github.io` |
| `MX` | `mx.zohomail.com` (10), `mx2.zohomail.com` (20) – Zoho, untouched |
| SPF / DKIM / DMARC | none published (left alone on purpose) |
| Record TTL | 3600 s |

The site went live on the custom domain on 2026-10-25 with HTTPS enforced.
The old server (`153.126.130.234`) is no longer referenced anywhere.

## New stack (decided)

- Hand-written HTML + one CSS file, no framework, no build step, no JavaScript.
- Hosted on **GitHub Pages**, published by a GitHub Actions workflow on every push to `main`.
- DNS stays at Sakura. Only the `A` record (→ GitHub Pages IPs) and a new `www` CNAME change; the Zoho MX records are not touched.
- Self-hosted fonts, no third-party requests, no cookies, no analytics.

See the design doc for why.

## Deployment

- **Host:** GitHub Pages, repository `kei178/tokyotranslator` (public).
- **Source:** GitHub Actions (`.github/workflows/pages.yml`); every push to
  `main` uploads `site/` and deploys it. No build step.
- **Custom domain:** `tokyotranslator.com` (set in the repo's Pages settings,
  "Enforce HTTPS" on). `www` redirects to the apex. Live since 2026-10-25.
- **Still to do (Task 10 in the plan):** renew the domain at Sakura before
  2026-11-30; after a week of the site working, cancel only the Sakura
  server contract.

## Working on the site locally

Everything the browser needs is in `site/`. There is no build step.

```bash
python3 -m http.server 8000 --directory site
```

Then open <http://localhost:8000/>, <http://localhost:8000/en/>, <http://localhost:8000/ja/>.

Before committing a change to the pages, run the static checks (no
scripts, no third-party URLs, correct `lang`/`hreflang`, assets exist, CSP
meta present) and the HTML validator:

```bash
python3 -I scripts/check.py
```

The check script has its own tests:

```bash
python3 -I -m unittest discover -s tests
```

```bash
npx --yes html-validate@8.29.0 site/index.html site/en/index.html site/ja/index.html site/404.html
```

(`html-validate` 8.x is pinned because newer releases need Node 20+.)

`scripts/images.py` is a one-off that produced `site/assets/img/` from the
originals recovered from the Wayback Machine; it needs Pillow.

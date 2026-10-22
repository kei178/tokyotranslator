# Static Site Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild tokyotranslator.com as three static HTML pages (de/en/ja) and put it live on GitHub Pages under the existing domain, with the DNS zone and the Zoho mail records left untouched at Sakura.

**Architecture:** Hand-written HTML in `site/` with one shared stylesheet, self-hosted fonts and locally stored images; no build step, no JavaScript. A GitHub Actions workflow publishes `site/` to GitHub Pages on every push to `main`. At Sakura only the apex `A` record changes (to the GitHub Pages IPs) and a `www` CNAME is added.

**Tech Stack:** HTML5, CSS3, GitHub Pages, GitHub Actions (`actions/upload-pages-artifact`, `actions/deploy-pages`). Verification only (never a build dependency): `npx html-validate`, `npx lighthouse`, `curl`, `dig`, Python 3 for a check script and image resizing.

**Spec:** `docs/superpowers/specs/2026-10-22-static-site-migration-design.md`

## Global Constraints

- No JavaScript anywhere in `site/`. No `<script>` tags.
- No request to any host other than the site itself. The only external URLs allowed in the HTML are the `hreflang`/canonical links to `https://tokyotranslator.com/...`, `mailto:quade@tokyotranslator.com`, and the GitHub privacy-statement link in the privacy section.
- URLs: German at `/`, English at `/en/`, Japanese at `/ja/`. Nothing else.
- No package.json, no lockfile, no `node_modules`, no build step in the workflow. Tools run via `npx --yes` or `python3` one-offs.
- Fonts: Lora 400 / 400 italic / 700 and Montserrat 300 / 400, latin subset, woff2, from `site/assets/fonts/`.
- Images: hero ≤ 250 KB, profile ≤ 60 KB.
- Every HTML page carries the two `<meta>` tags from spec §4.8 (CSP and referrer policy).
- The MX records at Sakura are never edited, deleted or re-created. No SPF/DKIM/DMARC is added.
- Content is copied from `reference/{de,en,ja}.html` with the spec §5 assumptions: Tokyo Ariake address with `〒135-0063` on all pages, "8 years" on all pages, current year in the footer, localized `<title>` and `<meta name="description">`.
- Every commit message ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

1. A visitor on a 360 px wide phone: nav links, the language switcher and the hero text must stay readable with no horizontal scroll. Pinned by the viewport check in Task 3.
2. A visitor who types `www.tokyotranslator.com` or `http://` must land on `https://tokyotranslator.com/`. Pinned in Task 9.
3. Any old deep link (`/en`, `/ja` without slash, `/feed/`, `/wp-login.php`) must not show a blank page: GitHub Pages resolves `/en` → `/en/` itself; everything else gets the trilingual 404. Pinned in Task 6 and Task 9.
4. A screen-reader user must hear the page in the right language: `lang` on `<html>`, and `lang` on the three language-switcher links that are not in the page language. Pinned in the check script (Task 3).
5. Mail to `quade@tokyotranslator.com` must be unaffected: the MX answer from `dig` is byte-for-byte the same before and after the Sakura edit. Pinned in Task 9.

---

## File map

| Path | Responsibility |
|---|---|
| `site/index.html` | German page (default) |
| `site/en/index.html` | English page |
| `site/ja/index.html` | Japanese page |
| `site/404.html` | trilingual not-found page (GitHub Pages serves it for unknown paths) |
| `site/.nojekyll` | empty; makes GitHub Pages serve files as-is |
| `.github/workflows/pages.yml` | publishes `site/` to GitHub Pages on push to `main` |
| `site/assets/css/style.css` | the one stylesheet, incl. `@font-face` |
| `site/assets/fonts/*.woff2` | Lora and Montserrat subsets |
| `site/assets/img/hero.jpg`, `hero.webp`, `profile.jpg`, `profile.webp` | images served |
| `site/assets/img/hero-2.jpg`, `hero-3.jpg` | spare slider images, not referenced |
| `scripts/check.py` | static checks over `site/` (run before every commit) |
| `scripts/images.py` | one-off: resize/compress the recovered images |

---

## Part A: build

Tasks 1–7 need only this repository.

### Task 1: Recover and optimize the images

**Files:**
- Create: `scripts/images.py`
- Create: `site/assets/img/hero.jpg`, `site/assets/img/hero.webp`, `site/assets/img/hero-2.jpg`, `site/assets/img/hero-3.jpg`, `site/assets/img/profile.jpg`, `site/assets/img/profile.webp`

**Interfaces:**
- Produces: the image paths above; `hero.jpg` is 1600 px wide, `profile.jpg` is 400×400.

- [ ] **Step 1: Download the four originals from the Wayback Machine into a scratch directory (not the repo)**

Use the `id_` flag so the archive returns the raw file, not a rewritten page:

```bash
mkdir -p /tmp/tt-img && cd /tmp/tt-img
curl -sSL -o profile.jpg  "https://web.archive.org/web/20220410023845id_/http://tokyotranslator.com/wp-content/uploads/2020/03/profile_nq.jpg"
curl -sSL -o slider1.jpg  "https://web.archive.org/web/20220522041946id_/http://tokyotranslator.com/wp-content/uploads/2017/06/tokyotranslator_slider1-1.jpg"
curl -sSL -o slider2.jpg  "https://web.archive.org/web/20180929063847id_/http://www.tokyotranslator.com/wp-content/uploads/2017/06/tokyotranslator_slider2-1.jpg"
curl -sSL -o slider3.jpg  "https://web.archive.org/web/20220522042703id_/http://tokyotranslator.com/wp-content/uploads/2017/06/tokyotranslator_slider3-1.jpg"
file *.jpg
```

Expected: `file` reports "JPEG image data" for all four. If any is HTML instead, retry with a different snapshot from `https://web.archive.org/cdx/search/cdx?url=<path>&output=json`.

- [ ] **Step 2: Write `scripts/images.py`**

`python3 -I scripts/images.py SRC_DIR OUT_DIR` using Pillow (`python3 -m pip install --user pillow` if missing). It writes `hero.jpg` (slider1, width 1600, quality 80, progressive), `hero.webp` (same, quality 78), `hero-2.jpg` and `hero-3.jpg` (slider2/3, same JPEG settings), `profile.jpg` (center-crop to square, 400×400, quality 85) and `profile.webp`. Strip EXIF on all outputs.

- [ ] **Step 3: Run it**

```bash
python3 -I scripts/images.py /tmp/tt-img site/assets/img
ls -l site/assets/img
```

Expected: six files; `hero.jpg` ≤ 250 KB, `profile.jpg` ≤ 60 KB. If `hero.jpg` is over budget, lower quality to 72 and rerun.

- [ ] **Step 4: Commit**

```bash
git add scripts/images.py site/assets/img
git commit -m "feat: recover and optimize site images from the Wayback Machine"
```

---

### Task 2: Self-host the fonts

**Files:**
- Create: `site/assets/fonts/lora-400.woff2`, `lora-400i.woff2`, `lora-700.woff2`, `montserrat-300.woff2`, `montserrat-400.woff2`
- Create: `site/assets/fonts/LICENSE-OFL.txt`

**Interfaces:**
- Produces: the five font files above with exactly those names; Task 3's `@font-face` rules reference them.

- [ ] **Step 1: Download latin woff2 subsets**

The google-webfonts-helper API returns ready-made subsets without any tooling:

```bash
mkdir -p /tmp/tt-fonts && cd /tmp/tt-fonts
curl -sSL -o lora.zip "https://gwfh.mranftl.com/api/fonts/lora?download=zip&subsets=latin&variants=regular,italic,700&formats=woff2"
curl -sSL -o montserrat.zip "https://gwfh.mranftl.com/api/fonts/montserrat?download=zip&subsets=latin&variants=300,regular&formats=woff2"
unzip -o lora.zip && unzip -o montserrat.zip && ls
```

Expected: five `.woff2` files. Fallback if the API is down: download the variable TTFs from `https://github.com/google/fonts` (`ofl/lora`, `ofl/montserrat`) and subset with `pyftsubset --flavor=woff2 --unicodes="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"` per weight.

- [ ] **Step 2: Copy into the repo under the fixed names and add the OFL license text**

Rename to the five names in the Files list. Put the SIL OFL 1.1 text (from either font's upstream repo) in `LICENSE-OFL.txt`.

- [ ] **Step 3: Verify**

```bash
ls -l site/assets/fonts && file site/assets/fonts/*.woff2
```

Expected: five files, each reported as "Web Open Font Format (Version 2)", each under 40 KB.

- [ ] **Step 4: Commit**

```bash
git add site/assets/fonts
git commit -m "feat: self-host Lora and Montserrat (latin subset, woff2)"
```

---

### Task 3: Stylesheet, check script, and the German page

**Files:**
- Create: `site/assets/css/style.css`
- Create: `site/index.html`
- Create: `scripts/check.py`

**Interfaces:**
- Produces: the HTML skeleton (header / hero / sections / footer, class names) that Tasks 4 and 5 copy; `python3 -I scripts/check.py` exits 0 when `site/` passes.

- [ ] **Step 1: Write `scripts/check.py` (the failing test)**

`python3 -I scripts/check.py` walks `site/**/*.html` and fails (exit 1, one line per failure) if any page:

- contains `<script`;
- contains `http://` or `https://` outside of (a) `hreflang`/`canonical` `<link>` tags pointing at `https://tokyotranslator.com/`, (b) `href="https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement"`;
- lacks the CSP `<meta http-equiv="Content-Security-Policy" ...>` tag or the `<meta name="referrer" ...>` tag with the exact values from spec §4.8;
- lacks `<html lang="xx">` where `xx` is `de` for `site/index.html` and `site/404.html`, `en` for `site/en/index.html`, `ja` for `site/ja/index.html`;
- (index pages only) lacks the four `hreflang` links (`de`, `en`, `ja`, `x-default`) with the exact URLs from spec §4.4;
- (index pages only) lacks a `<title>` and a `<meta name="description">`;
- (index pages only) lacks `mailto:quade@tokyotranslator.com`;
- (index pages only) lacks a language-switcher `<a>` for each of the other two languages carrying a `lang` attribute (`lang="en"` and `lang="ja"` on the German page, etc.);
- references a `src`/`href` under `/assets/` that does not exist on disk.

It also fails if `site/index.html`, `site/en/index.html`, `site/ja/index.html`, `site/404.html`, `site/.nojekyll`, `.github/workflows/pages.yml` are missing. (Tasks 4–6 create the rest; until then those failures are expected.)

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -I scripts/check.py`
Expected: exit 1, listing the missing files.

- [ ] **Step 3: Write `site/assets/css/style.css`**

Mobile-first, one breakpoint at `48rem`. Contains:

- five `@font-face` rules (`font-display: swap`) for the files from Task 2;
- `:root` tokens: `--text: #333`, `--muted: #666`, `--rule: #e5e5e5`, `--bg: #fff`, `--accent: #2a2a2a`, `--measure: 45rem`;
- `body`: Lora, 1.0625rem/1.75, `--text` on `--bg`; `html[lang="ja"] body` uses `"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans JP", Meiryo, sans-serif` and `line-height: 1.9`;
- headings: Montserrat 300; `h2` uppercase, letter-spacing `0.12em`, centered, with a 2.5rem × 1px `--rule` line under it (`::after`);
- `.site-header`: centered site title (`h1`, Montserrat 300, 2rem) and tagline; `.lang-switch` as an inline list separated by thin bars; `.site-nav` as a wrapping inline list of four links;
- `.hero`: full-bleed, `background: center/cover url(../img/hero.jpg)` with a `rgba(0,0,0,.45)` overlay, min-height `22rem`, white Montserrat text; `.hero li` is a tagline (uppercase strong line + regular subline); `@supports` the webp variant via a `.webp` class is **not** used — serve `hero.jpg` only in CSS, keep `hero.webp` for a future `<picture>`;
- `.section`: `max-width: var(--measure)`, centered, padding `3rem 1rem`; `.section + .section` has a top `--rule` border;
- `.profile`: flex row on ≥48rem, column below; `.profile img` is `10rem` round (`border-radius: 50%`), `object-fit: cover`;
- `.contact-list` and the "please include" list as plain `ul`;
- `.site-footer`: centered, `--muted`, 0.875rem;
- `a`: `--accent`, underlined, `:focus-visible` outline 2px.

- [ ] **Step 4: Write `site/index.html`**

Structure (same for all three pages; copy sentence by sentence from `reference/de.html`, applying spec §5 assumptions):

```
<!doctype html><html lang="de">
head: charset, viewport, CSP meta and referrer meta (spec §4.8), title, description, canonical https://tokyotranslator.com/, 4 hreflang links, stylesheet /assets/css/style.css, preload of lora-400.woff2 (crossorigin)
body
  a.skip-link → #main ("Zum Inhalt springen")
  header.site-header
    h1 Tokyo Translator  + p.tagline "Freiberufliche Übersetzerin für Japanisch | Englisch | Deutsch"
    nav.lang-switch aria-label="Sprache": <a href="/" aria-current="page">Deutsch</a> · <a href="/en/" lang="en">English</a> · <a href="/ja/" lang="ja">日本語</a>
    nav.site-nav aria-label="Hauptnavigation": #profil Mein Profil · #leistungen Leistungen · #preise Preise · #kontakt Kontakt
  section.hero aria-label="Leistungen im Überblick": ul with the 3 taglines (ÜBERSETZUNG FACHSPRACHLICHER TEXTE / aus den Bereichen Marketing, PR und Bewerbung; LITERATURÜBERSETZUNGEN / von Sachbüchern, Romanen und Kinderbüchern; KORREKTORAT DEUTSCHER TEXTE)
  main#main
    section#profil.section.profile: h2 Mein Profil; img /assets/img/profile.jpg alt="Nadine Quade" width=400 height=400; the three profile lines ("8 Jahre Berufserfahrung")
    section#leistungen.section: h2 Leistungen; h3 Meine Leistungen + ul(3); h3 Fachübersetzungen + paragraph; h4 Marketing & PR + paragraph; h4 Videospiellokalisierung + paragraph
    section#preise.section: h2 Preise; the two paragraphs (fix the doubled "erstellt" in the first one); ul of the 4 "please include" items; the "Alternativ…" sentence
    section#kontakt.section: h2 Kontakt; p "Bei Fragen oder für einen Kostenvoranschlag schreiben Sie mir gerne eine E-Mail:" + <a href="mailto:quade@tokyotranslator.com">quade@tokyotranslator.com</a>; p "Anhänge (z. B. den zu übersetzenden Text) können Sie direkt an die E-Mail anfügen."
    section#impressum.section: h2 Impressum; address block (Nadine Quade / Ariake Frontier Building Tower B / 3-7-26 Ariake, Koto-ku / 135-0063 Tokyo / Japan / E-Mail link)
    section#datenschutz.section: h2 Datenschutz; the privacy text below
  footer.site-footer: "© 2026 Tokyo Translator"
```

Privacy text (German): "Diese Website setzt keine Cookies, bindet keine Inhalte Dritter ein und erhebt keine personenbezogenen Daten. Sie wird über GitHub Pages (GitHub, Inc.) ausgeliefert; GitHub verarbeitet dabei technisch notwendige Verbindungsdaten (z. B. IP-Adresse) nach seiner <a href="https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement">Datenschutzerklärung</a>. Wenn Sie mir eine E-Mail schreiben, verwende ich Ihre Angaben ausschließlich zur Bearbeitung Ihrer Anfrage."

- [ ] **Step 5: Run the check script and the HTML validator**

```bash
python3 -I scripts/check.py
npx --yes html-validate site/index.html
```

Expected: `check.py` reports only the not-yet-created files (`en/index.html`, `ja/index.html`, `404.html`, `.nojekyll`, `pages.yml`) and nothing about `index.html`; `html-validate` reports 0 errors.

- [ ] **Step 6: Viewport check**

```bash
python3 -m http.server 8000 --directory site
```

Open `http://localhost:8000/` in the browser at 360 px and at 1280 px wide. Expected: no horizontal scrollbar at 360 px; nav and language links wrap onto two lines; hero text readable over the image; profile photo round; section titles uppercase with the rule beneath.

- [ ] **Step 7: Commit**

```bash
git add scripts/check.py site/assets/css/style.css site/index.html
git commit -m "feat: German home page, stylesheet and static checks"
```

---

### Task 4: English page

**Files:**
- Create: `site/en/index.html`

**Interfaces:**
- Consumes: the markup skeleton and class names from Task 3.

- [ ] **Step 1: Copy `site/index.html` to `site/en/index.html` and translate structure-for-structure from `reference/en.html`**

Differences from the German page: `lang="en"`; title `Tokyo Translator – Freelance Translator for Japanese | English | German`; description `Nadine Quade, freelance translator: specialist English and Japanese to German translation, machine translation post-editing and German proofreading.`; canonical `https://tokyotranslator.com/en/`; `aria-current` on the English switcher link, `lang="de"` on the Deutsch link and `lang="ja"` on the 日本語 link; nav anchors `#profile #services #rates #contact`; section ids to match; hero taglines, profile, services, rates text from `reference/en.html`; the "please include" list (not present on the old English page) translated from the German: source language, length of the text, text type / subject area, desired delivery date; contact paragraph "For inquiries or an individual quote, please email me:"; Impressum keeps the heading "Impressum" with the Tokyo address and `135-0063`; Privacy heading "Privacy" with the English rendering of the privacy text; footer unchanged. Asset paths stay absolute (`/assets/...`).

- [ ] **Step 2: Verify**

```bash
python3 -I scripts/check.py
npx --yes html-validate site/en/index.html
```

Expected: `check.py` no longer mentions `en/index.html`; validator 0 errors.

- [ ] **Step 3: Commit**

```bash
git add site/en/index.html
git commit -m "feat: English page"
```

---

### Task 5: Japanese page

**Files:**
- Create: `site/ja/index.html`

**Interfaces:**
- Consumes: skeleton from Task 3; the `html[lang="ja"]` font rules from `style.css`.

- [ ] **Step 1: Copy `site/index.html` to `site/ja/index.html` and fill from `reference/ja.html`**

Differences: `lang="ja"`; title `Tokyo Translator – 日本語・英語・ドイツ語 フリーランス翻訳者`; description `ナディーン・クァーデ（Nadine Quade）― 英語・日本語からドイツ語への専門翻訳、機械翻訳ポストエディット、ドイツ語校正。`; canonical `https://tokyotranslator.com/ja/`; switcher `lang="de"` / `lang="en"` on the two foreign links; nav labels プロフィール / サービス / 料金 / お問い合わせ with the same ids as the English page; profile line "翻訳家として8年間の実務経験" (spec §5 item 2); services as on the old page (note the old JA page has no video-game paragraph; do not add one); rates paragraphs; "please include" list in Japanese (原文の言語 / 文章の分量 / 文書の種類・分野 / 希望納期); contact "お問い合わせ又はお見積りのご依頼は、メールにてご連絡ください。" + mailto; 管理者情報 with the existing Japanese address (`〒135-0063 東京都江東区有明３－７－２６ 有明フロンティアビル タワーB`); プライバシーポリシー heading with the Japanese rendering of the privacy text; skip link "本文へ移動".

- [ ] **Step 2: Verify**

```bash
python3 -I scripts/check.py
npx --yes html-validate site/ja/index.html
```

Expected: `check.py` reports only `404.html`, `.nojekyll`, `pages.yml` missing; validator 0 errors. Open `http://localhost:8000/ja/` and confirm the body renders in a Japanese sans font (not Lora).

- [ ] **Step 3: Commit**

```bash
git add site/ja/index.html
git commit -m "feat: Japanese page"
```

---

### Task 6: 404 page, `.nojekyll`, deployment workflow

**Files:**
- Create: `site/404.html`, `site/.nojekyll`, `.github/workflows/pages.yml`

**Interfaces:**
- Produces: the workflow that Task 8 enables; Task 9 verifies the live domain.

- [ ] **Step 1: Write `site/404.html`**

`lang="de"`, same `<head>` metas as the German page, same header (no nav), one `main` with three short blocks: "Seite nicht gefunden" → link `/`; "Page not found" → `/en/`; "ページが見つかりません" → `/ja/`, each block with its own `lang` attribute. Uses the shared stylesheet via absolute path `/assets/css/style.css`.

- [ ] **Step 2: Create the empty marker file**

Run: `touch site/.nojekyll`

- [ ] **Step 3: Write `.github/workflows/pages.yml`**

Trigger `push` on `main` plus `workflow_dispatch`. Permissions `contents: read`, `pages: write`, `id-token: write`. One job `deploy` on `ubuntu-latest` with `environment: github-pages`, concurrency group `pages` (cancel-in-progress false), steps: `actions/checkout@v4`, `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3` with `path: site`, `actions/deploy-pages@v4` (id `deployment`). No build step.

- [ ] **Step 4: Verify**

```bash
python3 -I scripts/check.py && npx --yes html-validate site/404.html
```

Expected: `check.py` exits 0 with no output; validator 0 errors.

- [ ] **Step 5: Commit**

```bash
git add site/404.html site/.nojekyll .github/workflows/pages.yml
git commit -m "feat: 404 page and GitHub Pages deployment workflow"
```

---

### Task 7: Local quality gate

**Files:** none new.

- [ ] **Step 1: Lighthouse on all three pages**

With the local server running:

```bash
for p in / /en/ /ja/; do npx --yes lighthouse "http://localhost:8000$p" --preset=desktop --quiet --chrome-flags="--headless" --output=json --output-path=/tmp/lh$(echo $p | tr / _).json; done
python3 -I -c "import json,glob;[print(f, {k:round(v['score']*100) for k,v in json.load(open(f))['categories'].items()}) for f in glob.glob('/tmp/lh*.json')]"
```

Expected: Performance, Accessibility, Best Practices, SEO each ≥ 95 on every page. Fix and re-run until true. (Mobile run: drop `--preset=desktop`.)

- [ ] **Step 2: Third-party request check**

In the browser Network panel on each page: every request's host is `localhost`. Expected: zero other hosts.

- [ ] **Step 3: Update README "Working on the site locally" if anything changed, then commit**

```bash
git add README.md
git commit -m "docs: local verification notes"
```

---

## Part B: cutover runbook

Tasks 8–10 need the owner's GitHub repo settings and the Sakura control panel (spec §4.11). The builder prepares and verifies; the owner clicks. **Gate before Task 9:** the owner has reviewed all three pages on the GitHub Pages preview and confirmed the Impressum address, the experience figure and the privacy text. Zoho is never opened.

### Task 8: Enable GitHub Pages (owner performs the settings steps)

**Files:** none; settings recorded in `README.md` under a new "Deployment" heading.

- [ ] **Step 1: Make the repository public (spec §4.1)**

Run: `gh repo edit kei178/tokyotranslator --visibility public --accept-visibility-change-consequences`
Expected: `gh repo view --json visibility` prints `PUBLIC`. (Skip if the owner has GitHub Pro; Pages then works on the private repo.)

- [ ] **Step 2: Push `main` and set the Pages source to GitHub Actions**

```bash
git push origin main
gh api -X POST repos/kei178/tokyotranslator/pages -f build_type=workflow
gh workflow run pages.yml && gh run watch
```

Expected: the workflow run finishes green; `gh api repos/kei178/tokyotranslator/pages --jq .html_url` prints `https://kei178.github.io/tokyotranslator/`.

- [ ] **Step 3: Content review on the preview**

Open `https://kei178.github.io/tokyotranslator/`. Absolute asset paths (`/assets/...`) will not resolve on the project URL, so styling may be missing here; that is expected and fixes itself once the custom domain is set. Review the text of all three pages (`/`, `/en/`, `/ja/`) for the §5 assumptions. If the owner wants a styled preview before the domain switch, temporarily open the local server instead (Task 3 Step 6).

- [ ] **Step 4: Record the settings in README under "Deployment" and commit**

```bash
git add README.md && git commit -m "docs: GitHub Pages deployment settings"
```

---

### Task 9: Custom domain and the two Sakura records (owner performs; one short window)

**Files:** none; outcome recorded in `README.md` "Domain and DNS" table.

- [ ] **Step 1: Snapshot the mail records before touching anything**

```bash
dig +short MX tokyotranslator.com | sort | tee /tmp/mx-before.txt
```

Expected: `10 mx.zohomail.com.` and `20 mx2.zohomail.com.`.

- [ ] **Step 2: (Optional, recommended) verify the domain on GitHub**

GitHub → Settings (account) → Pages → Add a domain → `tokyotranslator.com`. GitHub shows a TXT record name `_github-pages-challenge-kei178` and a value. In the Sakura zone editor **add** that TXT record. Do not open any other row. Click Verify once `dig +short TXT _github-pages-challenge-kei178.tokyotranslator.com` returns the value.

- [ ] **Step 3: Set the custom domain on the repo**

Run: `gh api -X PUT repos/kei178/tokyotranslator/pages -f cname=tokyotranslator.com`
Expected: Settings → Pages shows `tokyotranslator.com` with "DNS check in progress".

- [ ] **Step 4: Edit the two web records at Sakura**

In the Sakura zone editor for `tokyotranslator.com`:

| Action | Row | New value |
|---|---|---|
| edit | `A` `@` `153.126.130.234` | `185.199.108.153` (then add three more `A @` rows: `185.199.109.153`, `185.199.110.153`, `185.199.111.153`) |
| add | `CNAME` `www` | `kei178.github.io.` |

Nothing else. The two `MX` rows are not opened.

- [ ] **Step 5: Verify DNS (TTL is 3600 s; allow up to an hour)**

```bash
dig +short A tokyotranslator.com | sort
dig +short CNAME www.tokyotranslator.com
dig +short MX tokyotranslator.com | sort | diff - /tmp/mx-before.txt && echo "MX unchanged"
```

Expected: the four GitHub IPs; `kei178.github.io.`; `MX unchanged`.

- [ ] **Step 6: Enforce HTTPS**

Once Settings → Pages shows "DNS check successful" and the certificate is issued (can take up to an hour after DNS resolves), tick **Enforce HTTPS**. Via CLI: `gh api -X PUT repos/kei178/tokyotranslator/pages -F https_enforced=true`.

- [ ] **Step 7: Verify the live site**

```bash
for u in https://tokyotranslator.com/ https://tokyotranslator.com/en/ https://tokyotranslator.com/ja/ http://tokyotranslator.com/ https://www.tokyotranslator.com/ https://tokyotranslator.com/en https://tokyotranslator.com/wp-login.php; do curl -sS -o /dev/null -L -w "$u -> %{url_effective} %{http_code}\n" "$u"; done
curl -sSI https://tokyotranslator.com/ | grep -i strict-transport-security
```

Expected: the three pages 200 at their own URL; `http://` and `www` end at `https://tokyotranslator.com/`; `/en` ends at `/en/` 200; `/wp-login.php` returns 404 and shows the trilingual 404 page in a browser; the HSTS header is present. Open each page in a browser once: styled, fonts loaded, no console errors, no third-party requests.

- [ ] **Step 8: Update the README "Domain and DNS" table to the new state and commit**

```bash
git add README.md && git commit -m "docs: site live on GitHub Pages, DNS records updated at Sakura"
```

---

### Task 10: Decommission Sakura (owner)

- [ ] **Step 1:** Renew the domain at Sakura (さくらのドメイン) before **2026-11-30**; the registration is through Sakura (registrar JPRS). Do this first, independently of everything else.
- [ ] **Step 2:** After one week of the site and mail working, cancel only the Sakura server/hosting contract that ran WordPress. Do not cancel the domain contract.
- [ ] **Step 3:** Note the renewal and cancellation dates in README under "Old stack" and "Domain and DNS".

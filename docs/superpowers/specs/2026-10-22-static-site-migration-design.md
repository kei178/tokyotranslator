# Design: migrate tokyotranslator.com from WordPress to a static site

Date: 2026-10-22
Status: draft, awaiting owner approval (builder check done 2026-10-22; hosting re-decided the same day after the owner ruled out touching the mail DNS)

## 1. Intent

tokyotranslator.com is the portfolio page of a freelance translator. It ran on
WordPress (PHP) on a Sakura Internet server. The owner shut the server down
because keeping a PHP/WordPress stack patched is not worth it for a site whose
content changes maybe once a year.

Rebuild the same site as static files, hosted somewhere that needs no
maintenance, and get the domain pointed at it. The site is down right now, so
speed matters more than polish, but the result should look at least as good as
the old site.

## 2. Goals, non-goals, anti-goals

Goals

- Same content and the same three languages as before: German, English, Japanese.
- German at `/`, English at `/en/`, Japanese at `/ja/`. Old links keep working.
- No server-side code anywhere. Nothing to patch.
- HTTPS on the apex domain.
- **The DNS zone stays at Sakura and the Zoho mail records (MX) are not
  touched at all.** The owner's words: mail works, don't risk it. Only the
  web records (`A @`, `CNAME www`) change.
- Deploy by pushing to `main`.

Non-goals

- A CMS, admin UI, or editing-without-git. The owner's developer edits HTML.
- A blog, news, or anything beyond the one landing page per language.
- Pixel-exact replication of the Graphy theme. Same feel, same fonts, same
  structure, simplified where it helps.
- Analytics.

Anti-goals (this would be a failure even if it "works")

- Any contact form or other backend. The form was the reason the site needed
  a server; it is removed on purpose.
- Any third-party JavaScript or third-party font loading. The audience is
  German-speaking; loading Google Fonts from Google's servers has drawn
  cease-and-desist letters in Germany since the 2022 Munich ruling.
- Any change to the MX records or a nameserver move. Both would mean
  re-creating the mail records, which the owner has ruled out.
- Introducing a build toolchain (Node, Ruby, Hugo) that will itself need
  updating in two years for a four-file site.

## 3. Constraints

- The old server is unreachable. The only copies of content and markup are
  the three HTML files in `reference/`. The four images are not in the repo
  but are archived in the Wayback Machine:
  - `http://web.archive.org/web/20220410023845/http://tokyotranslator.com/wp-content/uploads/2020/03/profile_nq.jpg`
  - `http://web.archive.org/web/20220522041946/http://tokyotranslator.com/wp-content/uploads/2017/06/tokyotranslator_slider1-1.jpg`
  - `http://web.archive.org/web/20180929063847/http://www.tokyotranslator.com/wp-content/uploads/2017/06/tokyotranslator_slider2-1.jpg`
  - `http://web.archive.org/web/20220522042703/http://tokyotranslator.com/wp-content/uploads/2017/06/tokyotranslator_slider3-1.jpg`
- DNS is hosted at Sakura Internet (`ns1.dns.ne.jp`, `ns2.dns.ne.jp`). Mail is
  on Zoho (`mx.zohomail.com`, `mx2.zohomail.com`). There is no `www` record
  and no SPF/DKIM/DMARC today. Record TTLs are 3600 s. The public zone may
  not be the whole zone (Zoho verification TXTs, subdomains); since the
  zone is not moving, those records simply stay where they are.
- The domain is registered through Sakura's domain service (registrar of
  record: JPRS). **It expires on 2026-11-30.** The Sakura *domain* contract
  stays and must be renewed; only the Sakura *server* contract goes away.
- Credentials needed for the cutover (GitHub repo settings, Sakura control
  panel) are the owner's. The builder does not hold them. Zoho is not
  touched.
- German law (§ 5 DDG, formerly TMG) requires an Impressum on a commercial
  site aimed at Germany. The Impressum section stays.

## 4. Decisions

Each decision below is the author's call unless marked "owner".

### 4.1 Hosting: GitHub Pages

Constraint first: the nameservers stay at Sakura. Sakura DNS supports plain
A, AAAA, CNAME, MX, TXT records, no ALIAS/ANAME and no CNAME at the apex. So
the host must accept the bare domain via fixed A records. That rules out:

| Option | Why not |
|---|---|
| Cloudflare Pages | an apex custom domain requires the zone to be on Cloudflare DNS (their docs: "you will need to add your site as a Cloudflare zone"); only subdomains work on external DNS |
| S3 + CloudFront | CloudFront has no fixed IPs; an apex needs a Route 53 alias, i.e. a nameserver move |

Remaining candidates, both with fixed apex IPs, automatic HTTPS and deploy-on-push:

| | GitHub Pages | Netlify |
|---|---|---|
| Apex on external DNS | 4 documented A records (`185.199.108–111.153`) | one A record `75.2.60.5` (documented fallback; Netlify prefers ALIAS) |
| Account needed | none new, repo is already on GitHub | new Netlify account + GitHub OAuth |
| Private repo | needs GitHub Pro; on a free plan the repo must be **public** | fine |
| Custom response headers | no (CSP via `<meta>` instead) | yes (`_headers`) |
| Server-side redirects | only `www`↔apex and trailing slash (automatic) | yes (`_redirects`) |
| Cost | free | free tier |

Decision: **GitHub Pages**, deployed by a GitHub Actions workflow that
uploads `site/`. The repository becomes public (owner confirms; everything
in it is already public content, the old HTML included). If the owner wants
the repo to stay private, the fallback is Netlify with the same `site/`
folder, and the only plan changes are the A record value, the `www` target,
and moving the headers/redirects from `<meta>` back into `_headers` /
`_redirects`.

### 4.2 DNS: stays at Sakura; two web records change

Nothing is moved. In the Sakura zone editor:

| Action | Record | Value |
|---|---|---|
| change | `A @` | replace `153.126.130.234` with the four GitHub Pages IPs `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` |
| add | `CNAME www` | `kei178.github.io` |
| add (optional, recommended) | `TXT _github-pages-challenge-kei178` | the token GitHub shows under Settings → Pages → verified domains; stops anyone else from claiming the domain on Pages |
| untouched | `MX @` ×2 | Zoho, as today |
| not added | SPF / DKIM / DMARC | the owner does not want mail DNS touched; left out on purpose |

GitHub Pages issues a Let's Encrypt certificate once the A records resolve
and "Enforce HTTPS" is ticked; `http://` and `www.` then redirect to
`https://tokyotranslator.com/`.

Rollout order: build and verify on the GitHub Pages preview first, set the
custom domain, change the two Sakura records, wait for the certificate,
enforce HTTPS, then cancel the Sakura server. See 4.11.

### 4.3 Site structure: three static HTML pages, no build step

```
site/
  index.html          German (default)
  en/index.html       English
  ja/index.html       Japanese
  404.html            GitHub Pages serves this for unknown paths
  .nojekyll           tells GitHub Pages to serve files as-is
  assets/
    css/style.css     the one stylesheet
    img/              hero + profile images (jpg, resized, plus webp)
    fonts/            Lora and Montserrat woff2 subsets
```

Three hand-written pages mean the header and footer are duplicated three
times. That is accepted: the site has one page, it changed about once a year,
and a templating step (Eleventy, Hugo, a Python script) would be more
maintenance than the duplication. If the site ever grows past one page per
language, introduce Eleventy at that point.

No JavaScript. The navigation is four anchor links that wrap on narrow
screens; no hamburger menu.

Deployment is one workflow, `.github/workflows/pages.yml`: on push to
`main`, upload `site/` with `actions/upload-pages-artifact` and publish it
with `actions/deploy-pages`. No build step inside the workflow either.

### 4.4 Language switching: separate pages, plain links

The language switcher is three links in the header (`Deutsch` / `English` /
`日本語`) pointing to `/`, `/en/`, `/ja/`. Each page carries:

```html
<html lang="de">
<link rel="alternate" hreflang="de" href="https://tokyotranslator.com/">
<link rel="alternate" hreflang="en" href="https://tokyotranslator.com/en/">
<link rel="alternate" hreflang="ja" href="https://tokyotranslator.com/ja/">
<link rel="alternate" hreflang="x-default" href="https://tokyotranslator.com/">
```

No automatic redirect by browser language: the owner wants German at `/`,
redirects confuse search engines and users alike, and a visitor can switch
in one click.

`<title>` and `<meta name="description">` are localized per page. The old
site showed the German tagline on all three languages; that is fixed.

### 4.5 Hero: one static image, three taglines

The Smart Slider 3 carousel (three slides, three images, jQuery) becomes a
single full-width hero with the first slider image as background and the
three taglines stacked as text over it. No animation. The other two slider
images are kept in the repo in case the owner wants them back.

### 4.6 Contact: email link replaces the form

The Kontakt / Contact / お問い合わせ section stays but contains one sentence
and a `mailto:quade@tokyotranslator.com` link, plus the "please include"
list that already lives in the Rates section (source language, length, text
type, deadline, or attach the file). The email address is written in plain
text; obfuscation is not worth the accessibility cost on a site whose
Impressum must show the address anyway.

### 4.7 Fonts: self-hosted Lora and Montserrat

Same typefaces as the old theme (Lora 400/400i/700 for body, Montserrat
300/400 for headings), as woff2 files in `site/assets/fonts/`, latin subset
only. Both are SIL Open Font License. The Japanese page uses the system
Japanese font stack for body text (the old theme did the same via `ja.css`).

### 4.8 Privacy and security

- GitHub Pages cannot set custom response headers, so each page carries
  `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; style-src 'self'; font-src 'self'; base-uri 'self'; form-action 'none'">`
  and `<meta name="referrer" content="strict-origin-when-cross-origin">`.
  `frame-ancestors`, `X-Content-Type-Options` and HSTS cannot be expressed
  in a meta tag; accepted, since the site has no scripts, no forms and no
  logged-in state. GitHub Pages sends HSTS itself on custom domains once
  HTTPS is enforced.
- No cookies, no analytics, no external requests of any kind.
- A short Datenschutz / Privacy section is added under the Impressum stating
  that the site sets no cookies, collects no data, and is served by GitHub
  Pages (naming GitHub, Inc. as hosting provider and linking to GitHub's
  privacy statement, `https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement`).
  Owner: review the wording; this is a legal text.

### 4.9 Design

Keep the Graphy look: white page, dark gray text, serif body (Lora), light
geometric sans headings (Montserrat) in uppercase for section titles, a thin
rule under section titles, centered single column of ~720px, generous
whitespace. Mobile first, one breakpoint around 768px. Profile photo
displayed as a circle next to the profile text.

### 4.10 What is dropped from the old pages

WordPress feeds, oEmbed, REST links, xmlrpc, emoji script, block-library CSS,
genericons, jQuery, Smart Slider, Contact Form 7, Bogo, the "Graphy by
Themegraphy" footer credit, "Skip to content" link (replaced by a proper one).

### 4.11 Who does what, and the gates

The work is two parts with a hard gate between them.

**Part A, the build** (Tasks 1–7 of the plan): done by the builder in this
repository. Ends with the site verified locally and pushed to `main`. Needs
no credentials beyond the GitHub repo.

**Part B, the cutover** (Tasks 8–10): a runbook the owner executes in the
GitHub repo settings and the Sakura zone editor, with the builder preparing
commands and checking results. Gates, in order:

1. The owner opens the GitHub Pages preview in all three languages and
   signs off the content, in particular the Impressum address and the
   Datenschutz text (both legal texts). Nothing goes on the real domain
   before this. This is also where the §5 assumptions get confirmed or
   corrected; the site is down today, so a quick review beats a long one.
2. In the Sakura zone editor only the `A @` record is changed and only
   `CNAME www` (plus the optional verification TXT) is added. The MX rows
   are not opened. `dig MX` before and after must match.
3. The site has served over HTTPS for a week before the Sakura server
   contract is cancelled.
4. The Sakura domain contract is never cancelled; it is renewed before
   2026-11-30.

## 5. Content to carry over, and what the owner must confirm

Content comes from `reference/{de,en,ja}.html` verbatim, except for the
items below. Each is a question for the owner; the plan uses the "assumed"
value until told otherwise.

| # | Issue | Assumed for now |
|---|---|---|
| 1 | Impressum address differs by language: DE shows Nishinomiya (Hyōgo), EN shows both Nishinomiya and Tokyo Ariake, JA shows only Tokyo Ariake (`〒135-0063`; EN has the typo `135-006`). Which address is current? | Tokyo Ariake, `135-0063`, on all three pages |
| 2 | Years of experience: DE/EN say 8, JA says 7. The pages date from 2017–2020, so both are probably stale. | "8" on all three pages until the owner gives a current number |
| 3 | Hero taglines mention book translation (Literaturübersetzungen), but the Services list does not. Keep as is? | keep as is |
| 4 | Privacy section wording (4.8). | draft text, owner reviews |
| 5 | SPF / DKIM / DMARC for Zoho are not published today. | Left alone on the owner's instruction; can be added any time later without touching the MX rows |
| 6 | Copyright year: old footer says 2026 (WordPress auto-year). | current year, hand-written |

## 6. Left to the builder

- Exact CSS values (spacing, type scale, colors) within the look described in 4.9.
- Image sizes and compression settings (target: hero ≤ 250 KB, profile ≤ 60 KB).
- Font subsetting tooling (pyftsubset or downloaded subsets from a font CDN
  mirror, committed as files either way).
- Wording of the 404 page (trilingual, links to the three home pages).
- Whether to inline the CSS into each page or keep one file. Either is fine.

## 7. Verification

- All three pages pass the W3C Nu HTML checker with no errors.
- Each page loads with zero third-party requests (check the Network panel).
- Lighthouse: Performance, Accessibility, Best Practices, SEO all ≥ 95 on mobile.
- `curl -I https://tokyotranslator.com/`, `/en/`, `/ja/` return 200;
  `http://tokyotranslator.com/` and `https://www.tokyotranslator.com/`
  redirect to the apex over HTTPS.
- `dig +short MX tokyotranslator.com` returns the same two Zoho records
  before and after the DNS edit.

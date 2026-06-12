# YDU PARTS — Homepage Mockup Brief (shared by all variants)

## Brand (extracted from live site — use EXACTLY)
- Logo (hotlink, wide banner ~3:1): https://ydu.com.au/wp-content/uploads/2024/11/banner.png
  (smaller: https://ydu.com.au/wp-content/uploads/2024/11/banner-300x103.png). Render ~44–56px tall in header on white/light chrome.
- Palette: primary `#4A90E2`; primary-hover `#6BB1FF`; dark navy text `#1B3A4B`; accent grey `#65696D`; light bg `#F1F4F6`; border `#DBDFE1`; white `#FFFFFF`; sale red `#FF0000` (use sparingly).
- Headings font: **Clash Grotesk** (weights 400–700) via Fontshare:
  `<link href="https://api.fontshare.com/v2/css?f[]=clash-grotesk@400,500,600,700&display=swap" rel="stylesheet">` — font-family: 'Clash Grotesk', sans-serif.
- Body font: system-ui stack (or Inter via Fontshare if desired).
- Tagline: **VW, AUDI and VAG Specialists**

## Required sections (order can vary by variant)
1. **Header**: logo, product search input, icons for account / wishlist / compare / cart (with count badges), nav: Shop, Contact, Check Your Order, Find Us. Sticky on scroll. Mobile: hamburger menu that actually opens (vanilla JS).
2. **Hero with VEHICLE FINDER** — the signature feature. Cascading selects: Make > Model > Submodel > Variant + a "Find Parts" button + reset. Make it functional with this demo data (vanilla JS, progressive enable):
   - Audi → A3 8P → Sportback → 2.0 TFSI / 1.8 TFSI; Audi → A4 B7 → Sedan → 2.0 TDI
   - Volkswagen → Golf Mk5 → Hatch → GTI / 2.0 FSI; Volkswagen → Golf Mk6 → Hatch → R
   - Skoda → Octavia → vRS → 2.0 TSI
3. **Trust strip**: Google 4.8★ rating, Fast nationwide delivery, Genuine & OEM parts with manufacturer warranty, Perth WA based.
4. **Category grid** (link tiles): Engine, Gaskets & Seals, Filters, Cooling System, Transmission, Electrical, Fuel System, Suspension, Body Parts, Performance, Interior.
5. **Featured products** (REAL data below): card = image, name, category chip, price, Add to Cart button + wishlist/quick-view icon affordances.
6. **Promo banners**: "60% OFF Car Batteries" + "WELCOME5 — 5% off storewide for new customers".
7. **Footer**: YDU PARTS, Unit 4/11 Weedon Road, Forrestdale WA 6112 · 0409 853 662 · info@ydu.com.au; links (Shop, Contact, Check Your Order, Find Us, Returns); payment method text badges (Visa, Mastercard, Amex, Apple Pay, Google Pay); ABN placeholder.

## Real products (hotlink images; prices ARE in AUD cents — format as $X,XXX.XX)
| Name | Price (cents) | Image | Category |
|---|---|---|---|
| SMP132532 – Pressure Sensor | 11814 | https://ydu.com.au/wp-content/uploads/2026/06/SMP132532.png | Transmission |
| 06L145612L – Turbo Electronic Wastegate Actuator | 47268 | https://ydu.com.au/wp-content/uploads/2026/06/06L145612L-2.webp | Engine |
| 06K121600E – HYBRID Water Pump (complete) | 64995 | (no image — use a neutral placeholder block with part number) | Engine |
| N90316801 – Coolant Temp Sensor O-Ring, VW Golf Mk4 Mk5 / Audi A4 B6 B7 | 1132 | https://ydu.com.au/wp-content/uploads/2026/01/N90316801.webp | Engine |
| WHT006407 – Engine Coolant Pipe O-Ring, VW Golf Mk5 Mk6 / Audi A4 B7 B8 | 814 | https://ydu.com.au/wp-content/uploads/2026/01/WHT006407.webp | Engine |
| 079919523B – Genuine Coolant Temp Sensor, Audi A4 B7 B8 / A6 C6 | 4177 | https://ydu.com.au/wp-content/uploads/2026/01/079919523B.webp | Engine |
| 1K0959455EA – Radiator Cooling Fan Large, VW Golf Mk5 Mk6 / Audi A3 8P | 20905 | https://ydu.com.au/wp-content/uploads/2026/01/1K0959455EA.webp | Engine |
| 1K0959455ES – Radiator Cooling Fan Small, VW Golf Mk5 Mk6 / Audi A3 8P | 18177 | https://ydu.com.au/wp-content/uploads/2026/01/1K0959455ES.webp | Engine |

## Quality bar (owner demands pixel-perfect)
- Single self-contained HTML file, no frameworks, vanilla JS only.
- Mobile-first responsive: flawless at 360, 375, 768, 1024, 1440px. No horizontal scroll ever.
- Consistent spacing scale (4/8px grid), aligned baselines, real hover/focus states, visible focus rings, smooth but subtle transitions (~150–250ms). Respect prefers-reduced-motion.
- Product images: object-fit contain on white, fixed aspect box so cards never jump.
- Lighthouse-minded: no layout shift, width/height or aspect-ratio on images, lazy-load below fold.
- Tasteful, premium automotive feel — this is a real store doing real revenue, not a template demo.

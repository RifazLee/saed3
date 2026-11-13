# Bolt Prompt: Multi-Language Internationalization for SAED Analyzer

## Overview

Add a language selection feature to the SAED Analyzer Pro app. The app must support 8 languages: **Indonesian (id), English (en), Chinese (zh), Japanese (ja), Dutch (nl), French (fr), Korean (ko), and Taiwanese (zh-TW)**. When the user changes the language, the entire UI switches instantly. PDF and CSV export outputs must also respect the selected language.

## Architecture Requirements

### 1. Language Context & Provider

- Create a React Context (`LanguageContext`) that holds:
  - `uiLanguage`: the language for the on-screen interface
  - `exportLanguage`: the language for PDF/CSV export output
  - `setUiLanguage(lang)`: changes the UI language
  - `setExportLanguage(lang)`: changes the export language independently
  - `t(key)`: translation function that returns the string for the current UI language
  - `tExport(key)`: translation function that returns the string for the current export language
- Persist both language selections in `localStorage` so they survive page reloads.
- Default `uiLanguage` to `'en'` and `exportLanguage` to `'en'` on first visit.
- Wrap the entire app in the `LanguageProvider` at the root level (in `App.tsx`).

### 2. Language Selector UI

- Add a language selector dropdown in the top-right header area of every authenticated page (materials database, material detail, calculator, diffraction analysis pages).
- The selector should show a globe icon (from lucide-react `Globe`) and the current language name in its own language (e.g., "English", "Bahasa Indonesia", "中文", "日本語", "Nederlands", "Français", "한국어", "臺灣話").
- Use a dropdown menu with all 8 languages listed, each showing the language name in its native script.
- Place TWO selectors side by side or in a small popover:
  - **UI Language** — controls what language the interface is displayed in
  - **Export Language** — controls what language PDF and CSV reports are generated in
- Include a short helper tooltip: "UI language controls the interface. Export language controls report output. These can be set independently."

### 3. Translation System

- Create a translation dictionary file structure under `src/i18n/`:
  ```
  src/i18n/
    index.ts          — exports t() and tExport() helpers, language list, type definitions
    en.ts             — English translations (base/baseline)
    id.ts             — Indonesian translations
    zh.ts             — Chinese (Simplified) translations
    zh-TW.ts          — Taiwanese (Traditional Chinese) translations
    ja.ts             — Japanese translations
    nl.ts             — Dutch translations
    fr.ts             — French translations
    ko.ts             — Korean translations
  ```
- Each translation file exports a flat or nested object keyed by translation keys (e.g., `material.name`, `button.generate`, `status.allowed`, `export.csv_header.hkl`).
- English (`en.ts`) is the baseline. All other files must cover the same set of keys.
- The `t(key)` function falls back to English if a key is missing in the selected language, and to the raw key string if missing in English too.

### 4. What to Translate

Translate ALL user-facing strings across every page:

**Pages to internationalize:**
- `LoginPage.tsx` — title, subtitle, labels, button text, error messages
- `MaterialPage.tsx` — all section headers (A–E), field labels, button text, table headers, status labels, empty-state messages, helper text, error messages, success messages, metric labels
- `MaterialDetailPage.tsx` — all labels, section headers, status badges, button text, validation actions, revision history labels
- `InputPage.tsx` — all labels, instructions, button text
- `ProcessingPage.tsx` — progress messages, status text
- `RingSelectPage.tsx` — all labels, instructions, button text, table headers
- `ResultsPage.tsx` — all labels, table headers, export button text, analysis summary text

**Common elements to translate:**
- Header titles and subtitles
- Button labels (Sign in, Sign out, Save, Export, Generate, Select All, etc.)
- Form field labels and placeholders
- Table column headers
- Status badges (Draft, Calculated, Pending Validation, Validated, Rejected)
- Reflection status labels (Allowed, Forbidden, Centering-compatible, Requires SG verification)
- Error messages and validation messages
- Success/toast messages
- Empty-state messages
- Helper/descriptive text
- Modal and dialog text
- Date formatting (use `Intl.DateTimeFormat` with the selected locale)

### 5. What NOT to Translate — Scientific Notation

The following must NEVER be translated and must remain identical across all languages:

- Scientific symbols: `F_{hkl}`, `S_{hkl}`, `HKL`, `d-spacing`, `Å` (Angstrom), `nm` (nanometer)
- Space group numbers (1–230)
- Hermann–Mauguin symbols (e.g., `Fm-3m`, `P6₃/mmc`)
- Crystal system names in formulas/scientific context — but the human-readable labels (e.g., "Cubic", "Tetragonal") SHOULD be translated in UI labels
- Lattice parameter symbols: `a`, `b`, `c`, `α`, `β`, `γ`
- Numerical values and units
- h, k, l indices
- Chemical formulas
- DOI strings and URLs
- Space group symbols and Hall symbols
- Wyckoff position letters

Only **labels, descriptions, explanations, button text, headers, and instructions** should be translated. Scientific notation, symbols, and formulas remain in their standard international form.

### 6. PDF Export Internationalization

- The PDF export (using jsPDF) must use `tExport()` instead of `t()` for all text content.
- PDF report headers, section titles, column headers, labels, and footer text must be in the export language.
- Scientific terms and symbols in the PDF remain untranslated (per section 5).
- The PDF filename can include a language-suffix (e.g., `SAED_Report_MaterialName_en.pdf`).
- Date and timestamp in the PDF should use `Intl.DateTimeFormat` with the export language locale.
- If the PDF uses any embedded font, ensure it supports CJK characters (Chinese, Japanese, Korean, Taiwanese). If jsPDF's default fonts don't support CJK, note this as a known limitation and fall back to Latin transliteration or English for CJK export languages, with a visible note in the UI.

### 7. CSV Export Internationalization

- CSV export must use `tExport()` for column headers and any text columns (e.g., status labels).
- Scientific columns (HKL, d-spacing values, 1/d², h, k, l) remain as-is.
- The CSV filename should include a language suffix (e.g., `MaterialName_HKL_en.csv`).
- Status text in CSV (Allowed, Forbidden, etc.) should be translated to the export language.

### 8. Language List & Locale Codes

```typescript
export const LANGUAGES = [
  { code: 'en', label: 'English', nativeLabel: 'English', locale: 'en-US', flag: '🇬🇧' },
  { code: 'id', label: 'Indonesian', nativeLabel: 'Bahasa Indonesia', locale: 'id-ID', flag: '🇮🇩' },
  { code: 'zh', label: 'Chinese (Simplified)', nativeLabel: '中文', locale: 'zh-CN', flag: '🇨🇳' },
  { code: 'zh-TW', label: 'Taiwanese (Traditional)', nativeLabel: '臺灣話', locale: 'zh-TW', flag: '🇹🇼' },
  { code: 'ja', label: 'Japanese', nativeLabel: '日本語', locale: 'ja-JP', flag: '🇯🇵' },
  { code: 'nl', label: 'Dutch', nativeLabel: 'Nederlands', locale: 'nl-NL', flag: '🇳🇱' },
  { code: 'fr', label: 'French', nativeLabel: 'Français', locale: 'fr-FR', flag: '🇫🇷' },
  { code: 'ko', label: 'Korean', nativeLabel: '한국어', locale: 'ko-KR', flag: '🇰🇷' },
] as const;

export type LanguageCode = typeof LANGUAGES[number]['code'];
```

### 9. Implementation Notes

- Replace ALL hardcoded user-facing strings across all `.tsx` files with `t('key')` calls.
- The current codebase has a mix of English and Indonesian hardcoded strings (especially in `MaterialPage.tsx`). All of these must be converted to translation keys.
- Do NOT use Google Translate or any external API for translations. Hardcode all translations in the translation files. Provide accurate, context-appropriate translations for each language. If you are unsure about a specific scientific-context translation, use the English term as a fallback.
- For languages you cannot confidently translate (e.g., Taiwanese), fall back to the closest language (Traditional Chinese) and note this in a comment.
- Ensure the language switch is instant — no page reload required. React Context propagation handles this.
- Maintain TypeScript type safety: the `t()` function should accept a string key and return a string.
- Do NOT translate content that comes from the database (material names, formulas, descriptions, notes entered by operators). Only translate the app's own UI strings.
- Operator-entered free-text fields (material description, notes) remain in whatever language the operator typed them in.

### 10. Export Language Independence (Key Requirement)

The export language is INDEPENDENT from the UI language. This means:

- An operator can use the Indonesian UI but export reports in English.
- An operator can use the English UI but export reports in Japanese.
- Both settings persist independently in localStorage.
- The PDF and CSV export functions must explicitly read from `exportLanguage` / `tExport()`, never from `uiLanguage` / `t()`.
- Add a brief note in the export section of the UI: "Reports will be generated in: [Export Language Name]" so the operator knows what language the output will be in before clicking export.

### 11. Testing Checklist

After implementation, verify:
- [ ] Language selector appears in the header on all authenticated pages
- [ ] Switching UI language instantly updates all visible text
- [ ] Switching export language does NOT change the UI text
- [ ] PDF export uses the export language for all labels and headers
- [ ] CSV export uses the export language for column headers and status text
- [ ] Scientific symbols (F_hkl, S_hkl, HKL, Å, nm) are NOT translated in any language
- [ ] Space group numbers and symbols are NOT translated
- [ ] Chemical formulas are NOT translated
- [ ] Both language selections persist across page reloads
- [ ] Date formatting respects the selected locale
- [ ] No hardcoded English or Indonesian strings remain in any .tsx file
- [ ] Build passes with no TypeScript errors
- [ ] All 8 languages have complete translation files

### 12. File Impact Summary

**New files:**
- `src/i18n/index.ts`
- `src/i18n/en.ts`
- `src/i18n/id.ts`
- `src/i18n/zh.ts`
- `src/i18n/zh-TW.ts`
- `src/i18n/ja.ts`
- `src/i18n/nl.ts`
- `src/i18n/fr.ts`
- `src/i18n/ko.ts`
- `src/i18n/LanguageContext.tsx` (context + provider + hook)
- `src/i18n/LanguageSelector.tsx` (UI dropdown component)

**Modified files:**
- `src/App.tsx` — wrap with LanguageProvider, pass language context
- `src/pages/LoginPage.tsx` — use t() for all strings
- `src/pages/MaterialPage.tsx` — use t() for all strings, use tExport() in exportCsv()
- `src/pages/MaterialDetailPage.tsx` — use t() for all strings, use tExport() in any export
- `src/pages/InputPage.tsx` — use t() for all strings
- `src/pages/ProcessingPage.tsx` — use t() for all strings
- `src/pages/RingSelectPage.tsx` — use t() for all strings
- `src/pages/ResultsPage.tsx` — use t() for all strings, use tExport() in PDF/CSV export
- `src/lib/diffraction/export.ts` — accept a translation function parameter, use it for headers/labels

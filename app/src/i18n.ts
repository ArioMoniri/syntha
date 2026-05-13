// Tiny i18n layer for the syntha desktop app.
//
// Two locales: en (English, default) and tr (Türkçe). The active locale
// is chosen by:
//   1. Persisted user preference in localStorage["syntha.locale"]
//   2. Otherwise navigator.language prefix
//   3. Otherwise "en"
//
// The UI re-renders by walking [data-i18n-key] elements on the page;
// see applyTranslations() below.

export type Locale = "en" | "tr";

interface Translation {
  // Header / tagline
  tagline_prefix: string;
  cohort_label: string;
  // Section 1 — cohort
  section_cohort: string;
  cohort_hint: string;
  cohort_tolerant: string;
  cohort_strict: string;
  ntrain_label: string;
  // Section 2 — parameters
  section_params: string;
  param_n: string;
  param_seed: string;
  param_constraints: string;
  param_constraints_hint: string;
  param_missingness: string;
  // Section 3 — actions
  section_generate: string;
  btn_generate: string;
  btn_preview: string;
  status_idle: string;
  // Preview
  section_preview: string;
  // Footer
  footer_license: string;
  footer_github: string;
  footer_check_updates: string;
  footer_lang_label: string;
}

const EN: Translation = {
  tagline_prefix: "Synthea-inspired synthetic patient record generator —",
  cohort_label: "Turkish pristine-healthy cohort",
  section_cohort: "1 · Choose a cohort",
  cohort_hint:
    "The Gaussian copula was fitted offline on real anonymized Turkish-cohort EHR episodes. Each cohort is a different inclusion criterion (strict = clinically pristine only; tolerant = mild comorbidity allowed).",
  cohort_tolerant: "Tolerant",
  cohort_strict: "Strict",
  ntrain_label: "n_train",
  section_params: "2 · Sampling parameters",
  param_n: "Number of episodes",
  param_seed: "Random seed",
  param_constraints: "Apply physiologic constraints",
  param_constraints_hint:
    "(pulse pressure, Friedewald, eGFR ↔ creatinine)",
  param_missingness: "Reproduce source-data missingness pattern",
  section_generate: "3 · Generate",
  btn_generate: "Generate & download CSV",
  btn_preview: "Preview first 10 rows",
  status_idle: "Idle. Pick a cohort and parameters, then click Generate.",
  section_preview: "Preview",
  footer_license:
    "Apache 2.0 · trained on open clinical standards (LOINC / SNOMED CT / ICD-10 / RxNorm) ·",
  footer_github: "GitHub",
  footer_check_updates: "Check for updates",
  footer_lang_label: "Language",
};

const TR: Translation = {
  tagline_prefix: "Synthea esintili sentetik hasta kaydı üretici —",
  cohort_label: "Türk pristine-sağlıklı kohortu",
  section_cohort: "1 · Bir kohort seçin",
  cohort_hint:
    "Gauss kopulası, gerçek anonimleştirilmiş Türk hasta kohortundaki EHR epizodları üzerinde eğitildi. Her kohort farklı bir dahil edilme kriterine sahiptir (strict = sadece klinik açıdan pristine; tolerant = hafif komorbiditeye izin verilir).",
  cohort_tolerant: "Tolerant",
  cohort_strict: "Strict",
  ntrain_label: "n_eğitim",
  section_params: "2 · Örnekleme parametreleri",
  param_n: "Epizot sayısı",
  param_seed: "Rastgele tohum",
  param_constraints: "Fizyolojik kısıtlamaları uygula",
  param_constraints_hint:
    "(nabız basıncı, Friedewald, eGFR ↔ kreatinin)",
  param_missingness: "Kaynak veri eksik veri desenini yeniden üret",
  section_generate: "3 · Üret",
  btn_generate: "Üret ve CSV indir",
  btn_preview: "İlk 10 satırı önizle",
  status_idle: "Bekliyor. Bir kohort ve parametre seçin, sonra Üret'e tıklayın.",
  section_preview: "Önizleme",
  footer_license:
    "Apache 2.0 · açık klinik standartlar üzerinde eğitildi (LOINC / SNOMED CT / ICD-10 / RxNorm) ·",
  footer_github: "GitHub",
  footer_check_updates: "Güncellemeleri kontrol et",
  footer_lang_label: "Dil",
};

const TRANSLATIONS: Record<Locale, Translation> = { en: EN, tr: TR };

const STORAGE_KEY = "syntha.locale";

export function detectLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "tr") return saved;
  } catch {
    /* localStorage unavailable in some sandboxed contexts */
  }
  const nav = (typeof navigator !== "undefined" && navigator.language) || "en";
  return nav.toLowerCase().startsWith("tr") ? "tr" : "en";
}

let currentLocale: Locale = "en";

export function setLocale(locale: Locale): void {
  currentLocale = locale;
  try {
    localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    /* ignore */
  }
  applyTranslations();
  document.documentElement.lang = locale;
}

export function getLocale(): Locale {
  return currentLocale;
}

export function t(key: keyof Translation): string {
  return TRANSLATIONS[currentLocale][key] ?? key;
}

/** Walk the DOM and substitute every [data-i18n-key]'s text content. */
export function applyTranslations(): void {
  document.querySelectorAll<HTMLElement>("[data-i18n-key]").forEach((el) => {
    const key = el.dataset.i18nKey as keyof Translation;
    const translated = TRANSLATIONS[currentLocale][key];
    if (translated !== undefined) {
      // For <input value> we set value; for everything else, textContent.
      if (el instanceof HTMLInputElement && el.dataset.i18nTarget === "value") {
        el.value = translated;
      } else if (el.dataset.i18nTarget === "html") {
        el.innerHTML = translated;
      } else {
        el.textContent = translated;
      }
    }
  });
}

/** Initialize the locale + render the locale switcher in the footer. */
export function initI18n(): void {
  currentLocale = detectLocale();
  document.documentElement.lang = currentLocale;
  applyTranslations();

  const switcher = document.getElementById("locale-switcher");
  if (switcher instanceof HTMLSelectElement) {
    switcher.value = currentLocale;
    switcher.addEventListener("change", () => {
      setLocale(switcher.value as Locale);
    });
  }
}

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
  param_longitudinal: string;
  param_longitudinal_hint: string;
  param_encounters_per_patient: string;
  param_years_of_history: string;
  param_clinical_only: string;
  param_clinical_only_hint: string;
  // Section 3 — actions
  section_generate: string;
  btn_generate: string;
  btn_preview: string;
  status_idle: string;
  // Preview
  section_preview: string;
  preview_hint: string;
  // Collaborate panel
  section_collaborate: string;
  collab_intro: string;
  collab_handle_label: string;
  collab_handle_placeholder: string;
  collab_handle_save: string;
  collab_handle_saved: string;
  collab_btn_refresh: string;
  collab_btn_claim: string;
  collab_badge_clinician: string;
  collab_badge_dev: string;
  collab_badge_data: string;
  collab_empty: string;
  collab_no_body: string;
  collab_opened_by: string;
  collab_offline: string;
  collab_fresh: string;
  collab_browse_github: string;
  collab_claim_modal_title: string;
  collab_claim_modal_intro: string;
  collab_claim_copy: string;
  collab_claim_copied: string;
  collab_claim_open_issue: string;
  collab_claim_close: string;
  collab_no_handle: string;
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
  param_longitudinal: "Longitudinal mode (multiple encounters per patient)",
  param_longitudinal_hint:
    "(synthesizes a shared HASTA_ID across episodes spread over several years; labs drift between visits)",
  param_encounters_per_patient: "Encounters per patient (Poisson mean)",
  param_years_of_history: "Years of history",
  param_clinical_only: "Clinical columns only (drop curation flags)",
  param_clinical_only_hint:
    "(hides BERTurk score, pristine_*, drug-safety flags, rf_* — training metadata, not real clinical signal)",
  section_generate: "3 · Generate",
  btn_generate: "Generate & download CSV",
  btn_preview: "Preview first 50 rows",
  status_idle: "Idle. Pick a cohort and parameters, then click Generate.",
  section_preview: "Preview",
  preview_hint: "Showing all columns; scroll horizontally for full width.",
  section_collaborate: "Collaborate",
  collab_intro:
    "syntha is open-source. Pick up a task tagged help-wanted-clinician, help-wanted-dev, or help-wanted-data and ship a contribution. Your GitHub handle is remembered locally so claim comments come from you.",
  collab_handle_label: "Your GitHub handle",
  collab_handle_placeholder: "octocat",
  collab_handle_save: "Save",
  collab_handle_saved: "Saved",
  collab_btn_refresh: "Refresh from GitHub",
  collab_btn_claim: "Claim this",
  collab_badge_clinician: "clinician",
  collab_badge_dev: "developer",
  collab_badge_data: "data / stats",
  collab_empty: "No open help-wanted tasks right now. Check back later, or browse the full repo on GitHub.",
  collab_no_body: "(no description yet)",
  collab_opened_by: "opened by",
  collab_offline: "Offline — last fetched",
  collab_fresh: "Fetched",
  collab_browse_github: "Browse all help-wanted issues on GitHub →",
  collab_claim_modal_title: "Claim a task",
  collab_claim_modal_intro:
    "Copy the comment below, then open the issue and paste it. The maintainers will see your handle and follow up.",
  collab_claim_copy: "Copy comment",
  collab_claim_copied: "Copied!",
  collab_claim_open_issue: "Open issue on GitHub",
  collab_claim_close: "Close",
  collab_no_handle: "Add your GitHub handle above first so the comment carries your identity.",
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
  param_longitudinal: "Longitudinal mod (hasta başına birden fazla ziyaret)",
  param_longitudinal_hint:
    "(birkaç yıla yayılan epizotlarda ortak bir HASTA_ID üretir; ziyaretler arasında laboratuvar değerleri kayar)",
  param_encounters_per_patient: "Hasta başına ziyaret (Poisson ortalaması)",
  param_years_of_history: "Geçmiş yıl sayısı",
  param_clinical_only: "Sadece klinik sütunlar (kohort etiketlerini gizle)",
  param_clinical_only_hint:
    "(BERTurk skoru, pristine_*, ilaç-güvenliği ve rf_* etiketleri gizlenir — bunlar eğitim meta verisi, gerçek klinik sinyal değil)",
  section_generate: "3 · Üret",
  btn_generate: "Üret ve CSV indir",
  btn_preview: "İlk 50 satırı önizle",
  status_idle: "Bekliyor. Bir kohort ve parametre seçin, sonra Üret'e tıklayın.",
  section_preview: "Önizleme",
  preview_hint: "Tüm sütunlar gösteriliyor; tam genişlik için yatay kaydırın.",
  section_collaborate: "Birlikte çalışın",
  collab_intro:
    "syntha açık kaynaklıdır. help-wanted-clinician, help-wanted-dev veya help-wanted-data etiketli bir görevi alın ve katkıda bulunun. GitHub kullanıcı adınız yerel olarak hatırlanır.",
  collab_handle_label: "GitHub kullanıcı adınız",
  collab_handle_placeholder: "octocat",
  collab_handle_save: "Kaydet",
  collab_handle_saved: "Kaydedildi",
  collab_btn_refresh: "GitHub'dan yenile",
  collab_btn_claim: "Bu görevi al",
  collab_badge_clinician: "klinisyen",
  collab_badge_dev: "geliştirici",
  collab_badge_data: "veri / ist.",
  collab_empty: "Şu an açık 'yardım aranıyor' görevi yok. Daha sonra tekrar bakın veya GitHub'da tüm depoyu inceleyin.",
  collab_no_body: "(açıklama yok)",
  collab_opened_by: "açan",
  collab_offline: "Çevrimdışı — son alındı",
  collab_fresh: "Alındı",
  collab_browse_github: "Yardım istenen tüm konuları GitHub'da inceleyin →",
  collab_claim_modal_title: "Görevi al",
  collab_claim_modal_intro:
    "Aşağıdaki yorumu kopyalayın, konuyu açın ve yapıştırın. Bakımcılar kullanıcı adınızı görüp size dönüş yapacak.",
  collab_claim_copy: "Yorumu kopyala",
  collab_claim_copied: "Kopyalandı!",
  collab_claim_open_issue: "Konuyu GitHub'da aç",
  collab_claim_close: "Kapat",
  collab_no_handle: "Yorumun size atfedilmesi için önce GitHub kullanıcı adınızı ekleyin.",
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

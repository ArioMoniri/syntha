# Türk Klinisyen Doğrulama Soruları — Toplu Review Tablosu

> **Bu dokümanın amacı:** syntha'da `help-wanted-clinician` etiketli (hem açık hem
> kapalı) GitHub Issue'larında ve kod incelemesinde ortaya çıkan klinik doğrulama
> ihtiyaçlarını **tek bir takip edilebilir tabloda** toplamaktır. Hedef, Türk
> klinisyenlerden klinik doğrulama almaktır.
>
> **Bu tablo klinik cevap ÜRETMEZ.** Yalnızca soruları ve bağlamı toplar.
> "Hekimin Cevabı" hücreleri **bilinçli olarak boştur**.
>
> **Bu çıktı doğrudan tedavi önerisi olarak kullanılmayacaktır;** ancak akademik ve
> teknik doğruluk için klinik onay gerekmektedir. Hekim cevapları girildikten sonra
> repodaki ilgili klinik modüller (clinical modules), tanı kodu eşlemeleri (FHIR
> mappings), referans aralıkları (reference ranges), ilaç seçim mantığı (medication
> logic) ve makale (manuscript) ifadeleri buna göre güncellenecektir.

---

## Bölüm 1 — Hekim İçin Klinik Doğrulama Tablosu

Bu tablo hekim içindir; teknik jargon en aza indirilmiştir. Lütfen yalnızca
"Hekimin Cevabı" ve "Kaynak / Kılavuz Önerisi" sütunlarını doldurun.

| Klinik Başlık | Sistem Şu An Ne Varsayıyor? | Hekime Sorulan Soru | Hekimin Cevabı | Kaynak / Kılavuz Önerisi | Not |
|---|---|---|---|---|---|
| Hipertansiyonda ilk tercih ilaç | İlk tercih lisinopril 10 mg/gün; kan basıncı çok yüksekse (sistolik ≥ 160 mmHg) ikinci ilaç olarak amlodipin ekleniyor | Türkiye'de rutin klinik pratikte hipertansiyonda ilk tercih ilaç hangisi olmalı, hangi dozda ve günde tek mi alınmalı? | | | Türkiye'de perindopril/ramipril ve nebivolol yaygın olarak kullanılıyor diye belirtilmiş |
| Böbrek hastalığı — evre eşikleri | Böbrek fonksiyonu (eGFR) KDIGO'ya göre 5 evreye (G1–G5) ayrılıyor | Türkiye'de eGFR'ye göre evre eşikleri (G1 ≥ 90, G2 60–89, G3a 45–59, G3b 30–44, G4 15–29, G5 < 15 mL/dk/1.73 m²) aynı şekilde mi kullanılıyor? | | | KDIGO uluslararası standarttır; Türkiye için teyit isteniyor |
| Böbrek hastalığı — nefroloji sevki | Sistem, böbrek fonksiyonu belirli bir eşiğin altına düştüğünde (G3b, yani eGFR < 45) hastayı nefrolojiye sevk ediyor gibi modelliyor | Türkiye'de hangi evrede nefrolojiye sevk uygundur — G3b'de mi yoksa G4'te mi? | | | Şu an varsayılan G3b; teyit gerekli |
| Böbrek hastalığı — idrar testi | Böbrek fonksiyonu G3a'nın (eGFR < 60) altındayken idrarda albümin/kreatinin oranı (ACR) testi isteniyor | Türkiye'de idrarda albümin/kreatinin oranı testi hangi evreden itibaren rutin olarak isteniyor? | | | |
| Böbrek hastalığı — sakınılacak ilaçlar | Düşük böbrek fonksiyonunda bakım planına "nefrotoksik (böbreğe zararlı) ilaçtan kaçın" notu ekleniyor; ilaç kesme/değiştirme yapılmıyor | Türkiye pratiğinde düşük eGFR'de özellikle sakınılması gereken ilaçlar hangileridir? | | | |
| Karaciğer yağlanması (MAFLD) değerlendirmesi | Sistemde henüz bu duruma özel bir değerlendirme yok | Türkiye'de hangi ALT/AST değerlerinde işlem yapılır, hangi tetkik istenir (USG? FibroScan?) ve ilk yaklaşım nedir (yaşam tarzı / ilaç)? | | | Yüksek prevalanslı; obezite vücut kitle indeksinden çıkarılıyor |
| Tanı kodu özgüllüğü — komplikasyonlu diyabet | Komplikasyonlu diyabet, "komplikasyonu belirtilmemiş" şeklinde kodlanıyor (E11.8) | Komplikasyonlu diyabette daha özgül bir tanı kodu (örn. hiperglisemi için E11.65) kullanmak uygun mu? | | | |
| Tanı kodu özgüllüğü — iskemik kalp hastalığı | İskemik kalp hastalığı "belirtilmemiş" şeklinde kodlanıyor (I25.9) | Geçirilmiş kalp krizi (enfarktüs) bilgisi varsa daha özgül bir kod (örn. eski MI için I25.2) kullanılmalı mı? | | | |
| Sistemde gösterilen Türkçe hastalık adları | Hastalık ve test adları Türkçeye birebir (mekanik) çevrilmiş | Bu Türkçe terimlerden hangileri klinik pratikte kullanılan doğru karşılık değil, nasıl düzeltilmeli? | | | Tam liste için bkz. **Ek A — Türkçe Klinik Terim Listesi** (her terim için ayrı doldurulabilir) |
| Anemi (kansızlık) değerlendirmesi | Sistemde henüz bu duruma özel bir değerlendirme yok | Hemoglobin düşükken Türkiye'de tipik tetkik sırası nedir (demir paneli? ferritin eşikleri? B12 ne zaman istenir?) ve ilk replasman (yerine koyma) yaklaşımı nasıldır? | | | |
| B12 eksikliği değerlendirmesi | Sistemde henüz modül yok; yalnızca B12 < 200 pg/mL bir referans olarak "düşük" işaretleniyor | Türkiye'de "eksik" ve "sınırda" B12 eşikleri nedir; replasman protokolü nasıldır (kas içi siyanokobalamin mi yoksa oral mı, hangi şema, hangi takip tetkikleri)? | | | Anemi değerlendirmesiyle sınırı netleştirilmeli |

---

## Bölüm 2 — Koddan Çıkan Ek Klinik Doğrulama İhtiyaçları

> Bu maddelerin GitHub'da ayrı bir `help-wanted-clinician` talebi **yoktu**; kod
> incelemesi sırasında tespit edildi. Yalnızca bunlardan en riskli görüleni (tiroid)
> için ayrıca bir GitHub Issue açılmıştır. Diğerleri, hekim cevabı geldikten sonra
> gerçekten değişiklik gerektirenler için issue açmak üzere şimdilik burada tutulur.

| Klinik Başlık | Sistem Şu An Ne Varsayıyor? | Hekime Sorulan Soru | Hekimin Cevabı | Kaynak / Kılavuz Önerisi | Not |
|---|---|---|---|---|---|
| Tiroid hastalığının otomatik hipotiroidi sayılması | "Tiroid hastalığı" işareti olan **her** hasta otomatik olarak hipotiroidi kabul edilip levotiroksin (50 mcg/gün) başlatılıyor; hipertiroidi/guatr hiç ele alınmıyor | Tiroid bozukluğu olan hastaların hepsini hipotiroidi varsaymak doğru mu; hipertiroidi ayrımı modellenmeli mi? | | | **Öncelik: Yüksek.** En riskli sessiz varsayım. Ayrıca GitHub Issue açıldı: #54 |
| Diyabette insülin başlama eşiği | Açlık kan şekeri ≥ 250 mg/dL ise veya "komplikasyonlu diyabet" işaretliyse insülin (glarjin) ekleniyor; ayrıca herkese metformin veriliyor | İnsülini başlatan eşik ve "komplikasyonlu" tanımı Türkiye pratiğine uygun mu? | | | Öncelik: Orta |
| Anksiyete + depresyon birlikteyken ilaç seçimi | Hasta hem depresyon hem anksiyete işaretliyse, çift SSRI'dan kaçınmak için anksiyeteye buspiron veriliyor | Eşzamanlı depresyon + anksiyetede bu yaklaşım uygun mu, yoksa tek bir SSRI'ın dozunu artırmak mı tercih edilmeli? | | | Öncelik: Orta. Kod yorumunda "klinik onaylı" yazıyor ancak kayıtlı bir klinisyen onayı bulunmuyor |
| Hiperlipidemide yüksek-yoğunluklu statin eşiği | LDL ≥ 190 mg/dL ise rosuvastatin, değilse atorvastatin başlatılıyor | LDL ≥ 190 eşiği ve statin seçimi Türkiye pratiğine uygun mu? | | | Öncelik: Orta |

---

## Bölüm 3 — Geliştirici Takip Tablosu (Developer Traceability)

> İngilizce tutulmuştur; implementasyon ekibi içindir. Hekimlerin bu tabloyu
> doldurması beklenmez.

| Issue | PR | Code section | Technical action | Priority | Status / notes |
|---|---|---|---|---|---|
| #16 | — | `modules/hypertension.py`, `fhir/rxnorm.py:ANTIHYPERTENSIVES` | Swap default first-line agent + dose per clinician answer | High | Open |
| #17a | #46 (merged, **no review**) | `fhir/codes.py:CKD_STAGES`, `modules/ckd.py:ckd_stage_for_egfr` | Confirm KDIGO eGFR cut-points for TR | High | **Closed-COMPLETED but clinically unverified** |
| #17b | #46 | `modules/ckd.py` (`REFERRAL_EGFR_THRESHOLD = 45.0`) | Confirm nephrology-referral stage (G3b vs G4) | High | Default G3b shipped without sign-off |
| #17c | #46 | `modules/ckd.py` (`ACR_EGFR_THRESHOLD = 60.0`) | Confirm ACR reflex trigger stage | High | |
| #17d | #46 | `modules/ckd.py` (`NEPHROTOXIC_AVOID` CarePlan note) | Define TR-specific nephrotoxic drugs to avoid | High | Currently a CarePlan note only |
| #18 | — | new `modules/mafld.py` | Author MAFLD module after clinician input | Medium | Open |
| #19a | partial in #46 | `fhir/codes.py:CONDITION_ICD10` (`DM_Komplikasyonlu`) | E11.8 → E11.65 (or per clinician) | Medium | Important for ICD coding + manuscript claims |
| #19b | — | `fhir/codes.py:CONDITION_ICD10` (`Iskemik_Kalp`) | I25.9 → I25.2 when prior-MI info present | Medium | |
| #20 | — | `locale/turkish.py:CONDITION_DISPLAY_TR` | Replace flagged TR strings (see Ek A) | Low | Open |
| #21 | — | new `modules/anemia.py` | Author anemia module | Medium | Open |
| #22 | — | new `modules/b12_deficiency.py` | Author B12 module; align with `reference_ranges.py` B12 band | Medium | Open |
| (no issue) | — | `modules/thyroid.py` | Model hyper- vs hypothyroid split | High | Code-derived; **new issue opened: #54** |
| (no issue) | — | `modules/diabetes.py` | Confirm insulin trigger (glucose ≥ 250 / complicated) | Medium | Code-derived |
| (no issue) | — | `modules/depression_anxiety.py:AnxietyModule` | Confirm buspirone-on-existing-SSRI pattern | Medium | Code-derived |
| (no issue) | — | `modules/hyperlipidemia.py` | Confirm LDL ≥ 190 high-intensity statin rule | Medium | Code-derived |

---

## Ek A — Türkçe Klinik Terim Listesi (Issue #20 için)

Aşağıdaki Türkçe gösterim metinleri (`Condition.code.text`) şu an mekanik çeviriyle
oluşturulmuştur. Lütfen her satır için "Uygun mu?" sütununa **Evet / Düzeltilmeli**
yazın; düzeltilmesi gerekenler için önerilen ifadeyi girin.

| Kaynak Bayrağı | Mevcut İngilizce (SNOMED) | Mevcut Türkçe | Uygun mu? (Evet/Düzeltilmeli) | Önerilen İfade | Not |
|---|---|---|---|---|---|
| Kanser | Malignant neoplastic disease | Habis neoplazi | | | |
| Iskemik_Kalp | Ischemic heart disease | İskemik kalp hastalığı | | | |
| Serebrovaskuler | Cerebrovascular disease | Serebrovasküler hastalık | | | |
| Kalp_Yetmezligi | Heart failure | Kalp yetmezliği | | | |
| Pulmoner_Emboli | Pulmonary embolism | Pulmoner emboli | | | |
| Aort_Anevrizma | Aortic aneurysm | Aort anevrizması | | | |
| Kronik_Bobrek | Chronic kidney disease | Kronik böbrek hastalığı | | | |
| Karaciger_Siroz | Cirrhosis of liver | Karaciğer sirozu | | | |
| Sepsis | Sepsis | Sepsis | | | |
| Atriyal_Fibrilasyon | Atrial fibrillation | Atriyal fibrilasyon | | | |
| COPD | Chronic obstructive pulmonary disease | Kronik obstrüktif akciğer hastalığı | | | |
| DM_Komplikasyonlu | Type 2 diabetes mellitus | Komplikasyonlu diabetes mellitus | | | |
| DM_Tum | Diabetes mellitus | Diabetes mellitus | | | |
| Astim | Asthma | Astım | | | |
| Hipertansiyon | Hypertensive disorder | Hipertansiyon | | | |
| Hiperlipidemi | Hyperlipidemia | Hiperlipidemi | | | |
| Tiroid | Disorder of thyroid gland | Tiroid hastalığı | | | |
| Obezite | Obesity | Obezite | | | |
| Depresyon | Depressive disorder | Depresyon | | | |
| Anksiyete | Anxiety | Anksiyete bozukluğu | | | |

---

## Kapsam ve Yöntem Notu

- Taranan Issue'lar: `help-wanted-clinician` etiketli tüm açık ve kapalı issue'lar
  (#16, #17, #18, #19, #20, #21, #22) — issue gövdeleri, yorumları ve ilgili
  Pull Request'ler (#46, #47) incelenmiştir.
- Klinik cevaplar **uydurulmamıştır**; "Hekimin Cevabı" sütunu boştur.
- **#17 hakkında not:** İlgili kod PR #46 ile birleştirilmiştir (merge), ancak
  PR'daki klinik doğrulama kontrol listesi onaylanmadan birleştirildiği için
  klinik doğrulama ihtiyacı henüz tam karşılanmamıştır. Bu nedenle issue'nun
  klinik takibi bu doküman üzerinden sürdürülmektedir.

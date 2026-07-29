# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · **Türkçe** ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->


> Bir Ajan Beceri çalışmasının ilk olarak nerede saptığını teşhis edin ve kanıtları inceleyin
> her sonucun arkasında.

Agent Skill Runtime IntelligenceAgent Skills için salt okunur bir çalışma zamanı kanıtı ve teşhis sistemidir. Beceri tanımlarını, resmi Agent çalışma zamanı olaylarını, içe aktarılan izleri, oturum geri dönüşünü ve gözlemlenebilir çalışma alanı sonuçlarını kanıta dayalı bir şekilde birleştirir.Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Hızlı başlangıç

Kimliği doğrulanmış bir sürümle özel depodan bağımsız sürümü yükleyin.GitMerkez CLI'si:

```bash
install_tmp="$(mktemp -d)"
gh release download --repo hellogxp/skill-runtime-intelligence \
  --pattern install.sh --dir "$install_tmp"
sh "$install_tmp/install.sh"
skill-runtime start
```

Veya doğrudan kaynak ödemesinden çalıştırın:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Açık[http://127.0.0.1:4317](http://127.0.0.1:4317). İçinCodex, yönetilen komutları inceleyin ve güvenin`/hooks`, yeni bir Temsilci turu başlatın ve ardından şunları doğrulayın:

```bash
.venv/bin/skill-runtime doctor
```

Entegrasyon, yalnızca gerçek bir resmi kanca etkinliği alındıktan sonra **Doğrulanmış** olur. Yapılandırılmış bir kanca **Beklemede** olarak gösterilir, hiçbir zaman canlı kanıt olarak gösterilmez.

| Ürün yüzeyi | Neye cevap veriyor |
|---|---|
| Çalışma Zamanına Genel Bakış | HangiSkillRunsilgiye mi ihtiyacınız var? |
| İlk Gözlemlenebilir Sınır | Kanıtlar ilk kez nerede kayboldu veya başarısız oldu? |
| Skill Run Panorama | İstek, aktivasyon, kaynaklar, araçlar, yapılar ve sonuç nasıl birbirine bağlandı? |
| Kanıt Müfettişi | Bu iddiayı hangi kaynak, derece, temel ve bağdaştırıcı yeteneği destekliyor? |
| Karşılaştırmak | Bir fark davranışsal mıdır, yoksa sadece gözlemlenebilir bir fark mıdır? |
| Ayarlar / Doktor | Okunan, saklanan, dışa aktarılan, bekleyen ve doğrulanan nedir? |

## Sorun

Bir Beceriyi yüklemek, onu bir temsilcinin keşfettiğini kanıtlamaz. Keşif aktivasyonu kanıtlamaz. Etkinleştirme, tüm talimatların ve kaynakların yüklendiğini kanıtlamaz. Uygulama, Becerinin sonucu iyileştirdiğini kanıtlamaz.

Bugün bu başarısızlıklar genellikle sessiz kalıyor. Geliştiriciler şunu sormaya devam ediyor:

- Beceri bu temsilcinin kullanımına açık mıydı?
- Bu istek için etkinleştirildi mi?
- Hangi talimatlar, referanslar, komut dosyaları ve varlıklar yüklendi?
- Hangi araçlar,MCPçağrılar, alt temsilciler, dosyalar ve yapılar işin içinde miydi?
- Çalıştırma nerede başarısız oldu, yeniden denendi veya bağlam kaybedildi?
- Beceri yardımcı oldu mu, yoksa yalnızca maliyet ve gecikmeyi mi arttırdı?

## Ürün yönü

İlk ürün bir **Skill Run Panorama**:

```text
User request
    ↓
Skills discovered
    ↓
Skill selected / not selected
    ↓
SKILL.md activated
    ↓
References and scripts loaded
    ↓
Tools / MCP / subagents executed
    ↓
Files and artifacts produced
    ↓
Observable outcome
```

Panorama, model öz raporundan değil, gerçek sinyallerden oluşturulmuştur:

| Kaynak | Örnekler | Kanıt |
|---|---|---|
| Beceri dosyaları | meta veriler, talimatlar, komut dosyaları, referanslar, varlıklar | Gözlemlendi |
| Çalışma zamanı etkinlikleri | Beceri çağrıları, araç çağrıları, alt aracılar, arızalar, süre | Gözlemlendi |
| Oturum transkriptleri | istemler, mesajlar, araç girişleri ve çıkışları, sıralama | Gözlemlendi |
| Çalışma alanı sonuçları | dosya değişiklikleri,Gitfark, raporlar, oluşturulan yapılar | Gözlemlendi |
| Korelasyon | olaylar, kaynaklar ve sonuçlar arasındaki ilişkiler | Türetilmiş veya Çıkartılmış |

## Kanıt disiplini

UIasla bir çıkarımı çalışma zamanı olgusu olarak sunmamalıdır:

- **Gözlemlendi** — bir kaynak etkinlikte veya dosyada açıkça mevcut.
- **Türetilmiş** — gözlemlenen kanıtlardan deterministik olarak bağlantılıdır.
- **Çıkarılan** — belirsizlik içeren makul bir açıklama.
- **Deneysel** — kontrollü ikili değerlendirme yoluyla ölçülen bir etki.

Tek bir izleme, yürütme ilişkilendirmesini destekleyebilir. Nedensel etkililiği kanıtlayamaz. “Bu Becerinin başarı oranını artırdığı” gibi iddialar, Becerili/Becerisiz değerlendirmenin tekrarlanmasını gerektirir.

## Ürün prensipleri

- Yerel, hibrit ve ekip bağlantılı dağıtımla varsayılan olarak özel.
- Salt okunur gözlem; asla temsilci döngüsünü devralmayın.
- Model proxy ve zorunlu bulut hizmeti yok.
- Varsayılan üründe engelleme, onay kapısı veya politika uygulaması yoktur.
- Açık kaynak ve kanıt derecelendirme.
- Aşamalı açıklama: Önce basit anlatım, isteğe bağlı ham olaylar.
- Aracı transkript formatlarını değiştirmek için bağdaştırıcı tabanlı destek.

## Başlangıç ​​kapsamı

MVP destekliyorClaude CodeVeCodexve şunları sağlar:

- yüklü Beceri keşfi ve doğrulaması;
- desteklendiğinde oturumu içe aktarma ve canlı yerel gözlem;
- Beceri aktivasyonu, kaynak yükleme ve araç çağrısı zaman çizelgeleri;
- alt temsilci,MCP, dosya ve yapıt ilişkileri;
- mevcut olduğunda süre, belirteç, hata, yeniden deneme ve durum özetleri;
- çalıştırma listesi, panorama DAG, etkinlik zaman çizelgesi ve düğüm denetçisi.

MVP, bir pazar yeri, evrensel aracı çalışma zamanı, güvenlik uygulaması, kurumsal yönetişim veya nedensel sonuç iddialarını **içermez**.

## Detaylı kurulum

Temel uygulamanın, bunun ötesinde hiçbir çalışma zamanı bağımlılığı yoktur.Python3.9+. Depo kökünden:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Sonra aç[http://127.0.0.1:4317](http://127.0.0.1:4317).

Tek seferlik`install`emretmek:

1. kullanıcı, proje ve önbelleğe alınmış eklenti Beceri konumlarını tarar;
2. tespit ederCodexVeClaude Codekonfigürasyonlarını değiştirmeden;
3. hangi Aracı ve Beceri yollarının okunacağını gösterir;
4. mevcut platform için sağlama toplamı doğrulanmış düşük başlangıçlı yerel göndericiyi indirir, yerel bir C yapısına geri döner ve son olarakPythongönderen ve kurulum sırasında yeni bir yerel ikili dosyayı önceden ısıtır;
5. yaratır`~/.skill-runtime/config.json`ve yerelSQLiteindeks.

Etkileşimli olarak çalıştırıldığında, arıza durumunda açılan Ajan kancalarını eklemeden önce bir kez sorar.`--no-hooks`transkript içe aktarmayı etiketli geri dönüş olarak tutarken,`--enable-hooks`açık rızayı kaydeder ve yalnızca yönetilen girişleri yükler. İçinCodex, açık`/hooks`kurulumdan sonra, yönetilen komutların tamamını gözden geçirin ve onlara güvenin.Codexyönetilen kurumsal yapılandırmanın dışına eklenen kancalar için bu açık incelemeyi kasıtlı olarak gerektirir. Yeni bir Temsilci dönüşü başlatın ve ardından şunu çalıştırın:

```bash
.venv/bin/skill-runtime doctor
```

Entegrasyon yalnızca veritabanı gerçek bir bildirim aldıktan sonra **Canlı** hale gelir`official_hook`etkinlik. Sadece yazmak`~/.codex/hooks.json`**Beklemede** olarak gösterilir, hiçbir zaman Bağlanmadı.`start`Toplayıcıyı, transkript geri dönüş izleyicisini, saklama çalışanını başlattı,SQLitedepola ve yaşaUIyönetilen bir arka plan süreci olarak. Hiçbir model isteği proxy'ye aktarılmaz.

Yaşam döngüsü komutları:

```bash
skill-runtime status
skill-runtime doctor
skill-runtime restart
skill-runtime stop
skill-runtime config --set retention_days=30
skill-runtime config --set network_export.endpoint=https://collector.example/v1/traces
skill-runtime config --set network_export.enabled=true
skill-runtime uninstall --keep-data
```

`uninstall`yalnızca yönetilen Hook girişlerini kaldırır veSkill Runtime-sahip olunan dosyalar. Olmadan`--keep-data`etkileşimli onay gerektirir (veya`--yes`) çıkarmadan önce`~/.skill-runtime`; Temsilci oturumları ve Beceri kaynakları hiçbir zaman kaldırılmaz.

Ayrı olarak dizine eklemek ve sunmak için:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Mevcut bir iz aktarımını ana gözlemlenebilirlik sisteminden içe aktarın:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

Sürümü belirlenmiş içe aktarma profilleri şu anda OTLP/'yi tanıyorPhoenix,Langfuse,LangSmith,W&B Weave, VeDatadog JSONşekiller. Sadece bir yaratırlarSkillRunkaynak açık Beceri anlambilimi taşıdığında; genel aralık adları etkinleştirme kanıtı olarak değerlendirilmez.

Normalleştirilmiş, Beceriye özgü çalışma zamanı kanıtlarını herhangi bir yere aktarınOTLP/HTTPuç noktayı izler:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Bir uç nokta açıkça yapılandırılmadığı sürece dışa aktarma devre dışı bırakılır. Kontrol noktaları, yeniden deneme durumu ve hedef durumu Ayarlar'da gösterilir. Ham istemler, araç verileri, kimlik bilgileri ve Beceri kaynağı içerikleri dışa aktarılmaz. Kimliği doğrulanmış arka planda dışa aktarma için standart sağlayın`OTEL_EXPORTER_OTLP_HEADERS`daha önce ortamda`skill-runtime start`; başlıklar asla yazılmazSkill Runtimeyapılandırma veya süreç argümanları.

## Canlı çalışma zamanı kanıtı gönder

`skill-runtime start`yerel bir Koleksiyoncu içerir. Yerel telemetri bağdaştırıcıları, resmi kancalar, hafif, arızalı açma kancaları veSDKentegrasyonlar tek bir olayı veya sınırlı bir toplu işlemi ekleyebilir`POST /api/events`:

```bash
curl -X POST http://127.0.0.1:4317/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "evt-example-activation",
    "event_type": "skill.activated",
    "occurred_at": "2026-07-29T05:00:00Z",
    "session_id": "agent-session-example",
    "turn_id": "turn-1",
    "activation_mode": "explicit_tool",
    "skill": {"name": "pdf"},
    "source": {
      "adapter": "example-agent",
      "adapter_version": "1.0",
      "collection_mode": "official_hook",
      "source_event_id": "source-event-1"
    },
    "evidence": {
      "grade": "observed",
      "confidence": 1.0,
      "basis": "Official runtime hook"
    },
    "payload": {"tool_name": "Skill"}
  }'
```

Uç nokta, kalıcılıktan önce ortak kimlik bilgilerini çıkarır ve tekilleştirir.`event_id`, redakte edilmiş ayrı bir ham zarfı korur ve elde edilen sonucu döndürür`skill_run_ids`.`GET /api/collector/schema`desteklenen olay sözlüğünü ve koleksiyon modlarını ortaya çıkarır.UIdinler`/api/stream`SSE kullanarak, yalnızca yeniden bağlanma geri dönüşü olarak yoklamayla.

Kaynak göstergesi, birincil çalışma zamanı kanıtlarını`Transcript fallback`ve ithal izler. Bir Collector uç noktası tek başına yerel telemetri iddiasında bulunmaz: her üretici, olayının yerel telemetriden mi, resmi bir kancadan mı, hafif bir kancadan mı yoksa bir yerel telemetriden mi geldiğini beyan etmelidir.SDK.

### İsteğe bağlı Ajan kancaları

Önce tam yolları ve olayları inceleyin. Bu komut salt okunurdur:

```bash
.venv/bin/skill-runtime setup
```

Kanca kurulumu açık bir bayrak gerektirir:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Yükleyici, Agent yapılandırmasını yedekler, mevcut kancaları korur ve yalnızca birSkill Runtimeyönetim işaretçisi. Kanca adaptörü, tam istemler veya araç yükleri yerine minimum yaşam döngüsü alanlarını depolar. Çalışma zamanı etkinken, izinleri kısıtlı birUnixsoket hızlı yoldur; isteğe bağlı bir yerel gönderen kaçınırPythonbaşlatmak. Çalışma zamanı etkin olmadığında, bağımsız arıza açma yolu, düzeltilmiş kanıtları`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`olay kimliği tekilleştirmeyle bu kuyruğu yeniden oynatır.

Codexetkinlikler resmi Kancasını kullanırAPI(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, Ve`Stop`).Codexşu anda komut kancalarını eşzamanlı olarak yürütüyor, bu nedenleSkill Runtimeyerel kullanırUnixsınırlı zaman aşımı olan soket/yerel gönderen. Herhangi bir teslimat hatası yutulur ve sıraya alınır; asla bir Temsilcinin kararını değiştirmez. Bkz.[resmi Codex Hook belgeleri](https://developers.openai.com/codex/config-advanced#hooks).

Yalnızca yönetilen girişleri şununla kaldırın:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Sunucu bağlanır`127.0.0.1`varsayılan olarak. Tam transkript mesajları ve araç yükleri dizine kopyalanmaz. Normalleştirilmiş özetler sürdürülmeden önce ortak gizli kalıplar düzeltilir.

Bağımlılık içermeyen test paketini şununla çalıştırın:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Sürüm mühendisliği

GitHub Eylemleri çalıştırılırPython3.9–3.13 testleri, JavaScript doğrulaması, yerel gönderen derlemesi ve gerçek bir yükleme/başlatma/doktora alma/durdurma/kaldırma duman testi. A`v*`etiketi, tekerlek/sdist paketlerinin yanı sıra sağlama toplamı korumalı Linux ve macOS yerel göndericileri oluşturur. CLI yükleyicisi eşleşen sürüm varlığını indirir, böylece son kullanıcıların bir derleyiciye ihtiyacı kalmaz.

Ürünle bağlantılı ilk teşhis deneyini çalıştırın:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Yaşam döngüsündeki kanıt boşluklarını, açık hataları, tamamlanmamış çalıştırmaları ve doğrulanmamış sonuçları hatayla enjekte eder, ardından sistem tarafından kullanılan aynı deterministik tanı motorunu değerlendirir.APIVeUI. Bkz.[PAI-DSW deney planı](docs/pai-dsw-experiment-plan.md)deney merdiveni, müdahalesizlik testleri ve tekrarlanabilirlik sözleşmesi için.

Tekerleği oluşturduktan sonra, izole edilmiş paketlenmiş yaşam döngüsü dumanını aşağıdakilerle çalıştırın:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Geçici bir sanal ortama ve geçici eve kurulur, kancaları etkinleştirmeden yerel yaşam döngüsünün tamamını uygular ve proje ile Aracı yapılandırmasının müdahalesiz olduğunu doğrular.

## Deney odaklı ürün tasarımı

Ürün davranışı aşağıdakiler tarafından sınırlandırılmıştır:[deney odaklı ürün felsefesi](docs/experiment-driven-product-philosophy.md): sonuçlardan önce kanıt, ciddiyetten önce ilk gözlemlenebilir sınır, düz kütüklerden önce yazılan ilişkiler ve olasılıksal yardımdan önce deterministik yeniden yapılanma.

Güncel tekrarlanabilir yerel kanıtlar şunları içerir:

- 7/7 yerel deney kapısı geçildi;
- Giriş/çıkış mutasyonu olmadan kabul edilen 2.400/2.400 Toplayıcı olayı;
- Desteklenmeyen nedensellik iddiası olmayan 14/14 deterministik hata bütünü teşhisleri;
- ilişkisel tanı gösterimi 13/14 kesin ve F1 0,963 iken düz yaşam döngüsü alımı 1/14 kesin ve F1 0,080'e ulaştı;
- 11/11 çalışma materyali vakalarında gözlemlenebilir en erken sınır ilk sıraya yerleştirilmiştir.

Bu sonuçlar, dağıtım genellemesini veya insan faydasını değil, mekanizmaları ve temsil seçeneklerini doğrular. Gerçek ikinci Ajan çalışmaları, platformlar arası kuyruk gecikmesi, gerçek hata kalibrasyonu ve katılımcı teşhis çalışmaları açık kanıt boşlukları olmaya devam ediyor.

Araştırmanın yönü aynı zamanda bitişikteki birincil çalışmaya da dayanmaktadır:[SkillsBench](https://arxiv.org/abs/2602.12670)Ve[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)Teşhisi motive eder çünkü Beceri etkileri değişkenlik gösterebilir ve gerileyebilir;[Harness-Bench](https://arxiv.org/abs/2605.27922)Yeteneğe duyarlı Aracılar arası karşılaştırmayı motive eder; ve[yürütme kaynağı araştırması](https://arxiv.org/abs/2606.04990)Yazılı kanıt ilişkilerini, iz kaynağını ve gizliliğe duyarlı denetim altyapısını motive eder.

## Dokümantasyon

- [Ürün tanımı](docs/product-definition.md)
- [MVP spesifikasyonu](docs/mvp-specification.md)
- [Çalışma zamanı olay modeli](docs/runtime-event-model.md)
- [Kullanıcı arayüzü bilgi mimarisi](docs/ui-information-architecture.md)
- [Adaptör yeteneği matrisi](docs/adapter-capability-matrix.md)
- [Gözlemlenebilirlik birlikte çalışabilirliği](docs/observability-interoperability.md)
- [Gözlemlenebilirlik platformu kurulumu](docs/observability-platform-setup.md)
- [Araştırma ve rekabet ortamı](docs/research-and-competitive-landscape.md)
- [Araştırma makalesi gündemi](docs/research-paper-agenda.md)
- [Deney odaklı ürün felsefesi](docs/experiment-driven-product-philosophy.md)
- [Deney sonuçları](docs/experiment-results-2026-07-29.md)
- [PAI-DSW deney planı](docs/pai-dsw-experiment-plan.md)

## Yol Haritası

1. **v0.1 — Çalışma zamanı kanıtı ve teşhisi:** canlı toplama,Skill Run Panorama, ilk sınır tanısı, kanıt incelemesi, karşılaştırma ve OTLP birlikte çalışabilirliği.
2. **v0.2 — Adaptör kapsamı ve teşhis çalışmaları:** ek Aracılar, gerçek Aracılar arası deneyler ve katılımcı değerlendirmesi.
3. **v0.3 — Etki değerlendirmesi:** Beceri ile/Beceri olmadan eşleştirilmiş değerlendirme ile kontrol edilir, tek seferlik teşhisten ayrı tutulur.

## Proje durumu

ASkillRun-ilk çalışma zamanı çalıştırılabilir: yüklü tanımlı envanter,Codextranskript geri dönüşü, izin odaklıCodexVeClaude Coderesmi kanca bağdaştırıcıları, aktif kapsam ilişkilendirmesi, tam dosya/yapı yolları, redaksiyon, ayrı kaynak/ilişki/çıkarım katmanları,SQLitedepolama, saklama, çapraz çalıştırma ve aracılar arası karşılaştırma, deterministik teşhis ve canlı PanoramaUI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, VeDatadogihracat ithal edilebilir; normalleştirilmiş kanıtlar, katılım yoluyla canlı olarak dışarı aktarılabilirOTLP/HTTP. Mevcut tekrarlanabilir paketin yedi adet geçiş deney kapısı vardır. Aday keşfi, model-iç seçim nedenleri, anlamsal etkililik ve nedensel sonuç iddiaları açıkça desteklenmemektedir.

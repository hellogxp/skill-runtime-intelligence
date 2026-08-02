# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · **Türkçe** ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Dönüş `SKILL.md` kontrol edilebilir çalışma zamanı beklentilerine dönüştürür. Aslında ne olduğunu görün
> davranışın ilk farklılaştığı yer ve kararın arkasındaki deliller.

Agent Skill Runtime Intelligence Agent Skills için salt okunur bir çalışma zamanı kanıtı ve teşhis sistemidir. Mevcut Beceri tanımından ihtiyatlı, denetlenebilir kısıtlamaları çıkarır, bunları çalışma zamanı etkinliğiyle eşleştirir ve sonucu kanıt dereceli bir sonuç olarak yeniden yapılandırır. Skill Run Panorama. Resmi Agent olaylarını, içe aktarılan izleri, etiketli oturum geri dönüşünü ve gözlemlenebilir çalışma alanı sonuçlarını, model isteklerini proxy olarak göndermeden veya Agent döngüsünü devralmadan birleştirir.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Hızlı başlangıç

En son sürümü yükleyin ve başlatın macOS veya Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Klon yok, hesap yok, `sudo`, veya GitHub CLI gereklidir. Yükleyici, sürüm sağlama toplamını doğrular, desteklenen Aracıları ve Becerileri algılar, okuyacağı her yolu açıklar, yalnızca gözlem kancalarını etkinleştirmeden önce bir kez sorar ve yerel UI en [http://127.0.0.1:4317](http://127.0.0.1:4317). Çalışma zamanı verileri aşağıda kalır `~/.skill-runtime` Açıkça bir dışa aktarma yapılandırmadığınız sürece.

Yapabilirsiniz [yükleyiciyi inceleyin](scripts/install.sh) çalıştırmadan önce.

### İlk canlı yayınınızı görün SkillRun

1. İsteğe bağlı arıza açmayı kabul edin Hook yükleyici sorduğunda kurulum.
2. Agent'ı yeniden başlatın ve yeni bir göreve başlayın. İçinde Codex, yönetilen komutları gözden geçirin `/hooks` Birinci; mevcut görevler yenilerini çalışırken yüklemiyor HookS.
3. Bir Beceriyi normal şekilde kullanın, ardından entegrasyonu onaylayın ve UI:

```bash
skill-runtime doctor
skill-runtime status
```

Bir entegrasyon yalnızca Toplayıcı gerçek bir çalışma zamanı olayı aldıktan sonra **Canlı** olur. Yapılandırılmış ancak gözlemlenmeyen Hook **Beklemede**—hiçbir zaman canlı kanıt olarak sunulmamıştır. Açık [http://127.0.0.1:4317](http://127.0.0.1:4317)veya bakın [Başlarken kılavuzu](docs/getting-started.md) Aracıya özel talimatlar ve sorun giderme için.

Doğrudan kaynak kullanıma alma işleminden çalıştırmak için:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Ürün yüzeyi | Neye cevap veriyor |
|---|---|
| Runtime Overview | Hangi SkillRuns ilgiye mi ihtiyacınız var? |
| Beceri Davranışı Kontrolü | Hangi kontrol edilebilir talimatlar karşılandı, gözden geçirilmesi gerekiyor veya değerlendirilemiyor? |
| Gerçekte Ne Oldu? | Hangi talimatlar, kaynaklar, araçlar, yapılar ve sonuçlar gözlemlendi? |
| First Observable Boundary | Çalışmaya özgü kanıtlar ilk olarak nerede kayboluyor veya başarısız oluyor? |
| Skill Run Panorama | İstek, etkinleştirme, kaynaklar, araçlar, yapılar ve sonuç nasıl birbirine bağlandı? |
| Evidence Inspector | Bu iddiayı hangi kaynak, derece, temel ve bağdaştırıcı yeteneği destekliyor? |
| Karşılaştırmak | Bir fark davranışsal mı yoksa sadece gözlemlenebilir bir fark mı? |
| Inferred Analysis | Hangi kanıta dayalı açıklama veya sonraki soruşturma makuldür? |
| Ayarlar / Doktor | Okunan, saklanan, dışa aktarılan, bekleyen ve doğrulanan şeyler nelerdir? |

## Nasıl çalışır?

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime Halihazırda kullandığınız iş akışını gözlemler. Sürümlendirilmiş bağdaştırıcılar, Aracıya özgü olayları istikrarlı bir Beceri yaşam döngüsüne dönüştürürken ham kaynak zarfları, normalleştirilmiş olaylar, ilişkiler ve çıkarımlar ayrı kalır. Teşhis motoru, açık Beceri kısıtlamalarını bu kanıtlara göre kontrol eder, gözlemlenebilir en erken sapmayı tanımlar ve sistemik bağdaştırıcının kör noktalarını çalıştırmaya özgü bulgulardan ayrı tutar. Model amacını veya nedensel etkililiği icat etmez.

| Veri kaynağı | Rol | Tazelik | UI etiket |
|---|---|---|---|
| Resmi Temsilci kancaları / eklentileri / SDK olaylar | Birincil yaşam döngüsü, araç, alt aracı ve terminal kanıtı | Canlı | `Official hook` / `Native telemetry` |
| Beceri dosyaları ve gözlemlenebilir çalışma alanı sonuçları | Tanım, kaynak, dosya, yapı ve test kanıtı | Canlı anlık görüntü / dizine eklendi | `Observed` |
| Oturum transkriptleri | Aracı yeterli çalışma zamanını kullanıma sunmadığında uyumluluk geri dönüşü API | Canlıya yakın veya tarihsel | `Transcript fallback` |
| OTLP ve desteklenen iz aktarımları | Birlikte çalışabilirlik ve tarihsel ithalat | Canlı dışa aktarma / toplu içe aktarma | Kaynak profili gösteriliyor |
| Deterministik korelasyon | Olayları bir şeye bağlar SkillRun kaynak gerçekleri değiştirmeden | Yutulduğunda | `Derived` |
| Anlamsal yardım | Yalnızca açıklamalar ve araştırma önerileri | Talep üzerine | `Inferred` |

Desteklenen birinci taraf bağdaştırıcılar bağımsız olarak sürümlendirilir:

| Ajan | Birincil entegrasyon | Geri çekilmek | Etkinleştirme görünürlüğü |
|---|---|---|---|
| Codex | Resmi komut HookS | Oturumu içe aktarma | Tarafından açığa çıkarıldığında açık aktivasyon Hook etkinlik |
| Claude Code | Resmi HookS | Oturumu içe aktarma | Açık Beceri aracı ve açığa çıkan eğik çizgi komutu kanıtı |
| Qoder | Resmi komut HookS | Yerel kayıtlar | Beceri aracı tarafından açığa çıkarıldığında açık aktivasyon |
| OpenCode | Yalnızca gözlem amaçlı küresel eklenti | Yerel kayıtlar | Açıkta kalan beceri aracı geri aramaları |

Kesin yetenek sınırları belgede belgelenmiştir. [adaptör yeteneği matrisi](docs/adapter-capability-matrix.md). Desteklenmeyen ve gözlemlenmeyen aşamalar arızalara dönüşmek yerine görünür kalır.

## Sorun

Bir Beceriyi yüklemek, onu bir temsilcinin keşfettiğini kanıtlamaz. Keşif aktivasyonu kanıtlamaz. Etkinleştirme, tüm talimatların ve kaynakların yüklendiğini kanıtlamaz. Talimatların yüklenmesi, Temsilcinin bunları takip ettiğini kanıtlamaz. Uygulama, Becerinin sonucu iyileştirdiğini kanıtlamaz.

Bugün bu başarısızlıklar genellikle sessiz kalıyor. Geliştiriciler şunu sormaya devam ediyor:

- Beceri bu temsilcinin kullanımına açık mıydı?
- Bu istek için etkinleştirildi mi?
- Hangi talimatlar, referanslar, komut dosyaları ve varlıklar yüklendi?
- Hangi açık Beceri gereksinimleri takip edildi, atlandı veya değerlendirilmesi imkansızdı?
- Hangi araçlar, MCP çağrılar, alt temsilciler, dosyalar ve yapılar işin içinde miydi?
- Çalıştırma nerede başarısız oldu, yeniden denendi veya bağlam kaybedildi?
- Beceri yardımcı oldu mu, yoksa yalnızca maliyet ve gecikmeyi mi arttırdı?

## Beceriye özgü tanı

Birincil teşhis nesnesi bir `SkillRun`, Agent oturumunun tamamı değil:

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

 UI yaşam döngüsünün düzenli, yazılı ve kanıt dereceli olmasını sağlar. Etkinleştirme telemetrisinin eksik olması "gözlenmediği" veya "desteklenmediği" anlamına gelir; Bu, Temsilcinin Beceriyi kesinlikle atladığı anlamına gelmez.

## Kanıt disiplini

 UI asla bir çıkarımı çalışma zamanı olgusu olarak sunmamalıdır:

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
- Açık kaynak ve kanıt sınıflandırması.
- Aşamalı açıklama: Önce basit anlatım, isteğe bağlı ham olaylar.
- Aracı transkript formatlarını değiştirmek için bağdaştırıcı tabanlı destek.

## Mevcut kapsam

Çalışma zamanı destekler Codex, Claude Code, Qoder, Ve OpenCode bağımsız, versiyonlu adaptörler aracılığıyla şunları sağlar:

- yüklü Beceri keşfi ve doğrulaması;
- gerçek zamanlı yetkili Hook/plugin koleksiyonu artı etiketli oturum geri dönüşü;
- Beceri aktivasyonu, kaynak yükleme ve araç çağrısı zaman çizelgeleri;
- alt temsilci, MCP, dosya ve yapıt ilişkileri;
- mevcut olduğunda süre, belirteç, hata, yeniden deneme ve durum özetleri;
- mevcut durumdan çıkarılan muhafazakar davranış kısıtlamaları `SKILL.md`;
- kanıta dayalı uyumluluk, doğrulama ve çalışma zamanı hatası kontrolleri;
- somut talimat, kaynak, araç, eser ve sonuç envanterleri;
- Runtime Overview çalışma bulgularından ayrılmış sistemik kapsam limitleri ile;
- birinci sınır tanısı;
- bir panorama DAG, etkinlik zaman çizelgesi ve kanıt denetçisi;
- yetenek bilincine sahip aynı Aracı ve aracılar arası karşılaştırma;
- ayrı Inferred Analysis çalışma zamanı gerçeklerini yeniden yazamayan yüzey;
- katılım OTLP/HTTP ihracat ve desteklenen gözlemlenebilirlik-iz ithalatı.

MVP, bir pazar yeri, evrensel aracı çalışma zamanı, güvenlik uygulaması, kurumsal yönetişim veya nedensel sonuç iddialarını **içermez**.

## Detaylı kurulum

Desteklenen en kısa yol için tek satırlık sürüm yükleyicisini kullanın. [Hızlı başlangıç](#quick-start). İlk çalıştırma akışının tamamı, Aracıya özel yeniden başlatma/güven adımları, gizlilik davranışı ve sorun giderme işlemleri, [Başlarken kılavuzu](docs/getting-started.md).

Geliştirme için, temel uygulamanın çalışma zamanı bağımlılığının ötesinde hiçbir bağımlılığı yoktur. Python 3.9+. Depo kökünden:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Sonra aç [http://127.0.0.1:4317](http://127.0.0.1:4317).

Tek seferlik `install` emretmek:

1. kullanıcı, proje ve önbelleğe alınmış eklenti Beceri konumlarını tarar;
2. tespit eder Codex, Claude Code, Qoder, Ve OpenCode konfigürasyonlarını değiştirmeden;
3. hangi Aracı ve Beceri yollarının okunacağını gösterir;
4. mevcut platform için sağlama toplamı doğrulanmış düşük başlangıçlı yerel göndericiyi indirir, yerel bir C yapısına geri döner ve son olarak Python gönderen ve kurulum sırasında yeni bir yerel ikili dosyayı önceden ısıtır;
5. yaratır `~/.skill-runtime/config.json` ve yerel SQLite indeks.

İlk dizin mevcut uyumlu Agent oturumlarını içe aktarır. Uzun ömürlü bir iş istasyonunda bu, yeni bir kurulumdan daha uzun sürebilir; daha sonraki başlangıçlar artımlıdır ve UI arka plan yenilemesi çalışırken kullanılabilir hale gelir.

Etkileşimli olarak çalıştırıldığında, arıza durumunda açılan Ajan kancalarını eklemeden önce bir kez sorar. `--no-hooks` transkript içe aktarmayı etiketli geri dönüş olarak tutarken, `--enable-hooks` açık rızayı kaydeder ve yalnızca yönetilen girişleri yükler. İçin Codex, açık `/hooks` kurulumdan sonra, yönetilen komutların tamamını gözden geçirin ve onlara güvenin. Codex yönetilen kurumsal yapılandırmanın dışına eklenen kancalar için bu açık incelemeyi kasıtlı olarak gerektirir. Yeni bir başlangıç ​​yap Codex güvendikten sonra görev/oturum Hooks, ardından şunu çalıştırın:

```bash
.venv/bin/skill-runtime doctor
```

Qoder yükler Hook başlangıçta yapılandırma, bu yüzden yeniden başlatın Qoder ilk kurulumdan sonra. OpenCode yönetilen yalnızca gözlem eklentisini global eklenti dizininden keşfeder; tekrar başlat OpenCode geçerli işlem kurulumdan önceyse. Entegrasyonların hiçbiri model isteklerini okumaz veya değiştirmez.

Entegrasyon yalnızca veritabanı gerçek bir bildirim aldıktan sonra **Canlı** hale gelir `official_hook` etkinlik. Sadece yazmak `~/.codex/hooks.json` **Beklemede** olarak gösterilir, hiçbir zaman Bağlanmadı. `start` Toplayıcıyı, transkript geri dönüş izleyicisini, saklama çalışanını başlattı, SQLite depola ve yaşa UI yönetilen bir arka plan süreci olarak. Hiçbir model isteği proxy'ye aktarılmaz.

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

`uninstall` yalnızca yönetilenleri kaldırır Hook girişler ve Skill Runtime-sahip olunan dosyalar. Olmadan `--keep-data`etkileşimli onay gerektirir (veya `--yes`) çıkarmadan önce `~/.skill-runtime`; Temsilci oturumları ve Beceri kaynakları hiçbir zaman kaldırılmaz.

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

Sürümü oluşturulmuş içe aktarma profilleri şu anda OTLP/'yi tanıyorPhoenix, Langfuse, LangSmith, W&B Weave, Ve Datadog JSON şekiller. Sadece bir yaratırlar SkillRun kaynak açık Beceri anlambilimi taşıdığında; genel yayılma adları etkinleştirme kanıtı olarak değerlendirilmez.

Normalleştirilmiş, Beceriye özgü çalışma zamanı kanıtlarını herhangi bir yere aktarın OTLP/HTTP uç noktayı izler:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Bir uç nokta açıkça yapılandırılmadığı sürece dışa aktarma devre dışı bırakılır. Kontrol noktaları, yeniden deneme durumu ve hedef durumu Ayarlar'da gösterilir. Ham istemler, araç verileri, kimlik bilgileri ve Beceri kaynağı içerikleri dışa aktarılmaz. Kimliği doğrulanmış arka planda dışa aktarma için standart sağlayın `OTEL_EXPORTER_OTLP_HEADERS` daha önce ortamda `skill-runtime start`; başlıklar asla yazılmaz Skill Runtime yapılandırma veya süreç argümanları.

## Canlı çalışma zamanı kanıtı gönder

`skill-runtime start` yerel bir Koleksiyoncu içerir. Yerel telemetri bağdaştırıcıları, resmi kancalar, hafif, arızalı açma kancaları ve SDK entegrasyonlar tek bir olayı veya sınırlı bir toplu işlemi ekleyebilir `POST /api/events`:

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

Uç nokta, kalıcılıktan önce ortak kimlik bilgilerini çıkarır ve tekilleştirir. `event_id`, redakte edilmiş ayrı bir ham zarfı korur ve elde edilen sonucu döndürür `skill_run_ids`. `GET /api/collector/schema` desteklenen olay sözlüğünü ve koleksiyon modlarını ortaya çıkarır. UI dinler `/api/stream` SSE kullanarak, yalnızca yeniden bağlanma geri dönüşü olarak yoklamayla.

Kaynak göstergesi, birincil çalışma zamanı kanıtlarını `Transcript fallback` ve ithal izler. Bir Collector uç noktası tek başına yerel telemetri iddiasında bulunmaz: her üretici, olayının yerel telemetriden mi, resmi bir kancadan mı, hafif bir kancadan mı yoksa bir yerel telemetriden mi geldiğini beyan etmelidir. SDK.

### İsteğe bağlı Ajan kancaları

Önce tam yolları ve olayları inceleyin. Bu komut salt okunurdur:

```bash
.venv/bin/skill-runtime setup
```

Hook kurulum açık bir bayrak gerektirir:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Yükleyici, Agent yapılandırmasını yedekler, mevcut kancaları korur ve yalnızca bir Skill Runtime yönetim işaretçisi. Kanca adaptörü, tam istemler veya araç yükleri yerine minimum yaşam döngüsü alanlarını depolar. Tamamlanan araç çağrıları için yalnızca kesin verileri çıkarır `SKILL.md`, standart Beceri kaynağı ve bellekteki değiştirilmiş dosya yolları; ham komutlar, yama gövdeleri, istemler ve araç çıktıları kalıcılıktan önce atılır. Çalışma zamanı etkinken, izinleri kısıtlı bir Unix soket hızlı yoldur; isteğe bağlı bir yerel gönderen kaçınır Python başlatmak. Çalışma zamanı etkin olmadığında, bağımsız arıza açma yolu, düzeltilmiş kanıtları `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` olay kimliği tekilleştirmeyle bu kuyruğu yeniden oynatır.

Codex etkinlikler resmi adını kullanır Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, Ve `Stop`). Codex şu anda komut kancalarını eşzamanlı olarak yürütüyor, bu nedenle Skill Runtime yerel kullanır Unix sınırlı zaman aşımı olan soket/yerel gönderen. Herhangi bir teslimat hatası yutulur ve sıraya alınır; asla bir Temsilcinin kararını değiştirmez. Bkz. [resmi Codex Hook belgeleri](https://developers.openai.com/codex/config-advanced#hooks).

Yalnızca yönetilen girişleri şununla kaldırın:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Sunucu bağlanır `127.0.0.1` varsayılan olarak. Tam transkript mesajları ve araç yükleri dizine kopyalanmaz. Normalleştirilmiş özetler sürdürülmeden önce ortak gizli kalıplar düzeltilir.

Bağımlılık içermeyen test paketini şununla çalıştırın:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Sürüm mühendisliği

GitHub Eylemler çalıştırılır Python 3.9–3.13 testleri, JavaScript doğrulaması, yerel gönderen derlemesi ve gerçek bir yükleme/başlatma/doktora alma/durdurma/kaldırma duman testi. A `v*` etiketi tekerlek/sdist paketleri artı sağlama toplamı korumalı oluşturur Linux Ve macOS yerli gönderenler CLI yükleyicisi eşleşen sürüm varlığını indirir, böylece son kullanıcıların bir derleyiciye ihtiyacı kalmaz.

Ürünle bağlantılı ilk teşhis deneyini çalıştırın:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Yaşam döngüsündeki kanıt boşluklarını, açık hataları, tamamlanmamış çalıştırmaları ve doğrulanmamış sonuçları hatayla enjekte eder, ardından sistem tarafından kullanılan aynı deterministik tanı motorunu değerlendirir. API Ve UI. Bkz. [PAI-DSW deney planı](docs/pai-dsw-experiment-plan.md) deney merdiveni, müdahalesizlik testleri ve tekrarlanabilirlik sözleşmesi için.

Tekerleği oluşturduktan sonra, izole edilmiş paketlenmiş yaşam döngüsü dumanını aşağıdakilerle çalıştırın:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Geçici bir sanal ortama ve geçici eve kurulur, kancaları etkinleştirmeden tüm yerel yaşam döngüsünü uygular ve proje ile Aracı yapılandırmasının müdahalesiz olduğunu doğrular.

## Deney odaklı ürün tasarımı

Ürün davranışı, deneye dayalı dört kısıtlamayı takip eder: sonuçlardan önce kanıtlar, ciddiyetten önce ilk gözlemlenebilir sınır, düz günlüklerden önce yazılı ilişkiler ve olasılıksal yardımdan önce deterministik yeniden yapılandırma.

Tekrarlanabilir deliller ve bunların sınırlamaları, [deney raporu](docs/experiment-results-2026-07-29.md). Sınırlandırılmış sonuçlar şunları içerir:

- Giriş/çıkış mutasyonu olmadan kabul edilen 2.400/2.400 Toplayıcı olayı;
- Desteklenmeyen nedensellik iddiası olmayan 14/14 deterministik hata bütünü teşhisleri;
- ilişkisel tanı gösterimi 13/14 kesin ve F1 0,963 iken düz yaşam döngüsü alımı 1/14 kesin ve F1 0,080'e ulaştı;
- doğrulanmış sonuçlar, dengeli Temsilciler arası kapsam ve insan etiketleri eksik olduğundan, doğrulayıcı ürün etkisi iddiaları için açıkça uygun olmayan, gizlilik açısından güvenli, gerçek bir denetim.

Bu sonuçlar, dağıtım genellemesini veya insan faydasını değil, mekanizmaları ve temsil seçeneklerini doğrulamaktadır. Gerçek ikinci Ajan çalışmaları, platformlar arası kuyruk gecikmesi, gerçek hata kalibrasyonu ve katılımcı teşhis çalışmaları açık kanıt boşlukları olmaya devam ediyor.

Araştırma yönü aynı zamanda bitişik birincil çalışmaya da dayanmaktadır: [SkillsBench](https://arxiv.org/abs/2602.12670) Ve [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) Teşhisi motive eder çünkü Beceri etkileri değişkenlik gösterebilir ve gerileyebilir; [Harness-Bench](https://arxiv.org/abs/2605.27922) Yeteneğe duyarlı Aracılar arası karşılaştırmayı motive eder; ve [yürütme kaynağı araştırması](https://arxiv.org/abs/2606.04990) Yazılan kanıt ilişkilerini, iz kaynağını ve gizliliğe duyarlı denetim altyapısını motive eder.

## Dokümantasyon

| Buradan başlayın | Amaç |
|---|---|
| [Getting Started](docs/getting-started.md) | Bir Temsilci kurun, bağlayın, canlı kanıtları doğrulayın ve sorunları giderin |
| [Mimarlık](docs/architecture.md) | Toplama hattı, depolama sınırları, kanıt motoru ve güven modeli |
| [Adaptör yeteneği matrisi](docs/adapter-capability-matrix.md) | Aracıya/sürüme göre kesin sinyaller ve sınırlamalar |
| [Gözlemlenebilirlik platformu kurulumu](docs/observability-platform-setup.md) | OTLP uyumlu platformları bağlayın ve desteklenen izleri içe aktarın |
| [Çalışma zamanı olay modeli](docs/runtime-event-model.md) | Kararlı olay sözlüğü, kaynağı, ilişkileri ve kanıt notları |
| [Kullanıcı arayüzü bilgi mimarisi](docs/ui-information-architecture.md) | Genel Bakış, İlk Sınır, Panorama, Denetleyici, Karşılaştırma ve Inferred Analysis |
| [Değişiklik günlüğü](CHANGELOG.md) | Kullanıcı tarafından görülebilen sürümlendirilmiş değişiklikler |
| [v0.3.0 sürüm notları](docs/releases/v0.3.0.md) | Yükseltme kılavuzu, öne çıkanlar ve bilinen sınırlar |

Ürün ve araştırma referansları: [ürün tanımı](docs/product-definition.md), [MVP spesifikasyonu](docs/mvp-specification.md), [gözlemlenebilirlik birlikte çalışabilirlik](docs/observability-interoperability.md), [deney sonuçları](docs/experiment-results-2026-07-29.md)ve [araştırma gündemi](docs/research-paper-agenda.md).

## Topluluk ve yönetim

- Okumak [Katkıda Bulunmak](CONTRIBUTING.md) Kanıt anlamını, bağdaştırıcılarını veya ürün davranışını değiştirmeden önce.
- Takip et [Davranış kodu](CODE_OF_CONDUCT.md) tüm proje alanlarında.
- Güvenlik açıklarını özel olarak bildirin [Güvenlik politikası](SECURITY.md), kamuya açık bir konu değil.
- Yapılandırılmış olanı kullanın [sorun izleyici](https://github.com/hellogxp/skill-runtime-intelligence/issues) tekrarlanabilir hatalar ve kapsamlı özellik önerileri için. Hiçbir zaman özel çalışma zamanı veritabanlarını veya oturum transkriptlerini eklemeyin.

## Yol Haritası

1. **v0.3.0 — Sonraki sürüm:** kontrol edilebilir Beceri davranışı kısıtlamaları, somut çalışma zamanı etkinliği, kanıta dayalı değerlendirme, sistemik kapsam tanısı ve mevcut canlı Panorama ve Karşılaştırma iş akışı.
2. **Sonraki — Bağdaştırıcı ve teşhisin güçlendirilmesi:** daha geniş Aracı/sürüm kapsamı, gerçek hata kalibrasyonu, platformlar arası kuyruk gecikmesi doğrulaması ve katılımcı teşhis çalışmaları.
3. **Daha sonra — Etki değerlendirmesi:** Beceri ile/Beceri olmadan eşleştirilmiş değerlendirme kontrol edilir, tek seferlik teşhisten açıkça ayrı tutulur.

## Proje durumu

Geçerli kaynak ağacı hedefleri `v0.3.0`; En son yayınlanan yapıyı belirlemek için yukarıdaki sürüm rozetini kullanın. Çalışma zamanı, kontrol edilebilir Beceri davranışı kısıtlamalarını, somut etkinlik özetlerini, yüklü tanımlı envanteri, izin odaklı resmi bilgileri içerir Hook için adaptörler Codex, Claude Code, Ve Qoder, yalnızca gözlem amaçlı OpenCode eklenti, etiketli transkript geri dönüşü, aktif kapsam ilişkilendirmesi, tam dosya/yapı yolları, redaksiyon, ayrı kaynak/ilişki/çıkarım katmanları, SQLite depolama, saklama, deterministik teşhis, canlı UIve çapraz çalıştırma/aracılar arası karşılaştırma. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, Ve Datadog ihracat ithal edilebilir; normalleştirilmiş kanıtlar, katılım yoluyla canlı olarak dışarı aktarılabilir OTLP/HTTP.

Model içindeki aday keşfi, model-iç seçim nedenleri, anlamsal etkililik ve nedensel sonuç iddiaları, bir kaynak veya kontrollü deney bu kanıtı sağlamadığı sürece açıkça desteklenmez.

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


> Bir Ajan Beceri çalışmasının ilk olarak nerede saptığını teşhis edin ve kanıtları inceleyin
> her sonucun arkasında.

Agent Skill Runtime Intelligence, Ajan Becerileri için salt okunur bir çalışma zamanı kanıt ve teşhis sistemidir. Beceri tanımlarını, resmi Agent çalışma zamanı olaylarını, içe aktarılan izleri, oturum geri dönüşünü ve gözlemlenebilir çalışma alanı sonuçlarını kanıt dereceli bir Skill Run Panorama'de birleştirir.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Hızlı başlangıç

En son sürümü macOS veya Linux'ye yükleyin ve başlatın:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Klon, hesap, `sudo` veya GitHub CLI gerekli değildir. Yükleyici, sürüm sağlama toplamını doğrular, desteklenen Aracıları ve Becerileri algılar, okuyacağı her yolu açıklar, yalnızca gözlem kancalarını etkinleştirmeden önce bir kez sorar ve [http://127.0.0.1:4317](http://127.0.0.1:4317)'de yerel UI'yi açar. Bir dışa aktarımı açıkça yapılandırmadığınız sürece çalışma zamanı verileri `~/.skill-runtime` altında kalır.

Çalıştırmadan önce [yükleyiciyi inceleyin](scripts/install.sh) yapabilirsiniz.

### İlk canlı yayınınızı görün SkillRun

1. Yükleyici sorduğunda isteğe bağlı arıza açma Hook kurulumunu kabul edin.
2. Agent'ı yeniden başlatın ve yeni bir göreve başlayın. Codex'de, önce `/hooks`'deki yönetilen komutları gözden geçirin; mevcut görevler yeni Hook'leri çalışırken yüklemez.
3. Bir Beceriyi normal şekilde kullanın, ardından entegrasyonu onaylayın ve UI'ı açın:

```bash
skill-runtime doctor
skill-runtime status
```

Bir entegrasyon yalnızca Toplayıcı gerçek bir çalışma zamanı olayı aldıktan sonra **Canlı** olur. Yapılandırılmış ancak gözlemlenmeyen bir Hook **Beklemede** durumundadır; hiçbir zaman canlı kanıt olarak sunulmaz. Aracıya özel talimatlar ve sorun giderme için [http://127.0.0.1:4317](http://127.0.0.1:4317)'i açın veya [Başlarken kılavuzu](docs/getting-started.md)'ye bakın.

Doğrudan kaynak kullanıma alma işleminden çalıştırmak için:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Ürün yüzeyi | Neye cevap veriyor |
|---|---|
| Runtime Overview | Hangi SkillRuns'e dikkat edilmesi gerekiyor? |
| First Observable Boundary | Kanıtlar ilk kez nerede kayboldu veya başarısız oldu? |
| Skill Run Panorama | İstek, aktivasyon, kaynaklar, araçlar, yapılar ve sonuç nasıl birbirine bağlandı? |
| Evidence Inspector | Bu iddiayı hangi kaynak, derece, temel ve bağdaştırıcı yeteneği destekliyor? |
| Karşılaştırmak | Bir fark davranışsal mıdır, yoksa sadece gözlemlenebilir bir fark mıdır? |
| Inferred Analysis | Hangi kanıta dayalı açıklama veya sonraki soruşturma makuldür? |
| Ayarlar / Doktor | Okunan, saklanan, dışa aktarılan, bekleyen ve doğrulanan nedir? |

## Nasıl çalışır?

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime halihazırda kullanmakta olduğunuz iş akışını gözlemler. Sürümlendirilmiş bağdaştırıcılar, Aracıya özgü olayları istikrarlı bir Beceri yaşam döngüsüne dönüştürürken ham kaynak zarfları, normalleştirilmiş olaylar, ilişkiler ve çıkarımlar ayrı kalır. Teşhis motoru öncelikle kanıtların kaybolduğu veya başarısız olduğu en erken sınırı belirler; model amacını veya nedensel etkililiği icat etmez.

| Veri kaynağı | Rol | Tazelik | UI etiketi |
|---|---|---|---|
| Resmi Temsilci kancaları / eklentileri / SDK etkinlikleri | Birincil yaşam döngüsü, araç, alt aracı ve terminal kanıtı | Canlı | `Official hook` / `Native telemetry` |
| Beceri dosyaları ve gözlemlenebilir çalışma alanı sonuçları | Tanım, kaynak, dosya, yapı ve test kanıtı | Canlı anlık görüntü / dizine eklendi | `Observed` |
| Oturum transkriptleri | Aracı yeterli çalışma zamanı sunmadığında uyumluluk geri dönüşü API | Canlıya yakın veya tarihsel | `Transcript fallback` |
| OTLP ve desteklenen iz aktarımları | Birlikte çalışabilirlik ve tarihsel ithalat | Canlı dışa aktarma / toplu içe aktarma | Kaynak profili gösteriliyor |
| Deterministik korelasyon | Kaynak gerçeklerini değiştirmeden olayları SkillRun'a bağlar | Yutulduğunda | `Derived` |
| Anlamsal yardım | Yalnızca açıklamalar ve araştırma önerileri | Talep üzerine | `Inferred` |

Desteklenen birinci taraf bağdaştırıcılar bağımsız olarak sürümlendirilir:

| Ajan | Birincil entegrasyon | Geri çekilmek | Etkinleştirme görünürlüğü |
|---|---|---|---|
| Codex | Resmi komut Hooks | Oturumu içe aktarma | Hook olayı tarafından açığa çıkarıldığında açık aktivasyon |
| Claude Code | Resmi Hook'lar | Oturumu içe aktarma | Açık Beceri aracı ve açığa çıkan eğik çizgi komutu kanıtı |
| Qoder | Resmi komut Hooks | Yerel kayıtlar | Beceri aracı tarafından açığa çıkarıldığında açık aktivasyon |
| OpenCode | Yalnızca gözlem amaçlı küresel eklenti | Yerel kayıtlar | Açıkta kalan beceri aracı geri aramaları |

Kesin yetenek sınırları [adaptör yeteneği matrisi](docs/adapter-capability-matrix.md)'da belgelenmiştir. Desteklenmeyen ve gözlemlenmeyen aşamalar arızalara dönüşmek yerine görünür kalır.

## Sorun

Bir Beceriyi yüklemek, onu bir temsilcinin keşfettiğini kanıtlamaz. Keşif aktivasyonu kanıtlamaz. Etkinleştirme, tüm talimatların ve kaynakların yüklendiğini kanıtlamaz. Uygulama, Becerinin sonucu iyileştirdiğini kanıtlamaz.

Bugün bu başarısızlıklar genellikle sessiz kalıyor. Geliştiriciler şunu sormaya devam ediyor:

- Beceri bu temsilcinin kullanımına açık mıydı?
- Bu istek için etkinleştirildi mi?
- Hangi talimatlar, referanslar, komut dosyaları ve varlıklar yüklendi?
- Hangi araçlar, MCP çağrıları, alt aracılar, dosyalar ve yapılar dahil edildi?
- Çalıştırma nerede başarısız oldu, yeniden denendi veya bağlam kaybedildi?
- Beceri yardımcı oldu mu, yoksa yalnızca maliyet ve gecikmeyi mi arttırdı?

## Beceriye özgü tanı

Birincil tanılama nesnesi bir `SkillRun`'dır, Aracı oturumunun tamamı değil:

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

UI asla bir çıkarımı çalışma zamanı gerçeği olarak sunmamalıdır:

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

## Mevcut kapsam

Çalışma zamanı, bağımsız, sürümlendirilmiş bağdaştırıcılar aracılığıyla Codex, Claude Code, Qoder ve OpenCode'yi destekler ve şunları sağlar:

- yüklü Beceri keşfi ve doğrulaması;
- gerçek zamanlı resmi Hook/eklenti koleksiyonu artı etiketli oturum geri dönüşü;
- Beceri aktivasyonu, kaynak yükleme ve araç çağrısı zaman çizelgeleri;
- alt aracı, MCP, dosya ve yapıt ilişkileri;
- mevcut olduğunda süre, belirteç, hata, yeniden deneme ve durum özetleri;
- Runtime Overview ve birinci sınır tanısı;
- bir panorama DAG, etkinlik zaman çizelgesi ve kanıt denetçisi;
- yetenek bilincine sahip aynı Aracı ve aracılar arası karşılaştırma;
- çalışma zamanı gerçeklerini yeniden yazamayan ayrı bir Inferred Analysis yüzeyi;
- OTLP/HTTP dışa aktarmayı tercih edin ve gözlemlenebilirlik izleme içe aktarımını destekleyin.

MVP, bir pazar yeri, evrensel aracı çalışma zamanı, güvenlik uygulaması, kurumsal yönetişim veya nedensel sonuç iddialarını **içermez**.

## Detaylı kurulum

Desteklenen en kısa yol için [Hızlı başlangıç](#quick-start)'deki tek satırlı sürüm yükleyiciyi kullanın. İlk çalıştırma akışının tamamı, Aracıya özgü yeniden başlatma/güven adımları, gizlilik davranışı ve sorun giderme işlemleri [Başlarken kılavuzu](docs/getting-started.md)'de yayınlanmaktadır.

Geliştirme için, temel uygulamanın Python 3.9+ ötesinde çalışma zamanı bağımlılığı yoktur. Depo kökünden:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Daha sonra [http://127.0.0.1:4317](http://127.0.0.1:4317)'ı açın.

Tek seferlik `install` komutu:

1. kullanıcı, proje ve önbelleğe alınmış eklenti Beceri konumlarını tarar;
2. yapılandırmalarını değiştirmeden Codex, Claude Code, Qoder ve OpenCode'yi algılar;
3. hangi Aracı ve Beceri yollarının okunacağını gösterir;
4. geçerli platform için sağlama toplamı doğrulanmış düşük başlangıçlı yerel göndericiyi indirir, yerel C yapısına ve son olarak Python göndericiye geri döner ve kurulum sırasında yeni bir yerel ikili dosyayı önceden ısıtır;
5. `~/.skill-runtime/config.json` ve yerel SQLite dizinini oluşturur.

Etkileşimli olarak çalıştırıldığında, arıza durumunda açılan Ajan kancalarını eklemeden önce bir kez sorar. `--no-hooks` etiketli yedek olarak transkript içe aktarmayı korurken, `--enable-hooks` açık izni kaydeder ve yalnızca yönetilen girişleri yükler. Codex için kurulumdan sonra `/hooks`'yi açın, yönetilen komutların tamamını inceleyin ve onlara güvenin. Codex, yönetilen kurumsal yapılandırmanın dışına eklenen kancalar için bu açık incelemeyi kasıtlı olarak gerektirir. Hook'lara güvendikten sonra yeni bir Codex görevi/oturum başlatın ve ardından şunu çalıştırın:

```bash
.venv/bin/skill-runtime doctor
```

Qoder başlangıçta Hook yapılandırmasını yükler, bu nedenle ilk kurulumdan sonra Qoder'yi yeniden başlatın. OpenCode küresel eklenti dizininden yönetilen yalnızca gözlem eklentisini keşfeder; Mevcut işlem kurulumdan önceyse OpenCode'yi yeniden başlatın. Entegrasyonların hiçbiri model isteklerini okumaz veya değiştirmez.

Entegrasyon yalnızca veritabanı gerçek bir `official_hook` olayı aldıktan sonra **Canlı** olur. Yalnızca `~/.codex/hooks.json` yazmak **Beklemede** olarak gösterilir, hiçbir zaman Bağlanmadı. `start`, Toplayıcıyı, transkript geri dönüş izleyicisini, saklama çalışanını, SQLite mağazasını ve yönetilen bir arka plan işlemi olarak canlı UI'yi başlatır. Hiçbir model isteği proxy'ye aktarılmaz.

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

`uninstall` yalnızca yönetilen Hook girişlerini ve Skill Runtime'ye ait dosyaları kaldırır. `--keep-data` olmadan, `~/.skill-runtime`'yi kaldırmadan önce etkileşimli onay (veya `--yes`) gerekir; Temsilci oturumları ve Beceri kaynakları hiçbir zaman kaldırılmaz.

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

Sürümlendirilmiş içe aktarma profilleri şu anda OTLP/Phoenix, Langfuse, LangSmith, W&B Weave ve Datadog JSON şekillerini tanımaktadır. Yalnızca kaynak açık Beceri semantiğini taşıdığında bir SkillRun oluştururlar; genel aralık adları etkinleştirme kanıtı olarak değerlendirilmez.

Normalleştirilmiş, Beceriye özgü çalışma zamanı kanıtlarını herhangi bir OTLP/HTTP izleme uç noktasına aktarın:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Bir uç nokta açıkça yapılandırılmadığı sürece dışa aktarma devre dışı bırakılır. Kontrol noktaları, yeniden deneme durumu ve hedef durumu Ayarlar'da gösterilir. Ham istemler, araç verileri, kimlik bilgileri ve Beceri kaynağı içerikleri dışa aktarılmaz. Kimlik doğrulamalı arka planda dışa aktarma için, `skill-runtime start`'den önce ortamda `OTEL_EXPORTER_OTLP_HEADERS` standardını sağlayın; başlıklar hiçbir zaman Skill Runtime konfigürasyon veya süreç argümanlarına yazılmaz.

## Canlı çalışma zamanı kanıtı gönder

`skill-runtime start` yerel bir Koleksiyoncu içerir. Yerel telemetri bağdaştırıcıları, resmi kancalar, hafif, arızalı açma kancaları ve SDK entegrasyonları, `POST /api/events`'ye tek bir olayı veya sınırlı bir grubu ekleyebilir:

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

Uç nokta, kalıcılıktan önce ortak kimlik bilgilerini çıkarır, `event_id` ile tekilleştirir, düzeltilmiş ayrı bir ham zarfı korur ve elde edilen `skill_run_ids` değerini döndürür. `GET /api/collector/schema` desteklenen etkinlik kelime dağarcığını ve koleksiyon modlarını gösterir. UI, SSE kullanarak `/api/stream`'yi dinler ve yoklama yalnızca yeniden bağlanma geri dönüşü olarak yapılır.

Kaynak göstergesi, birincil çalışma zamanı kanıtlarını `Transcript fallback` ve içe aktarılan izlerden ayırır. Collector uç noktası tek başına yerel telemetri iddiasında bulunmaz: her üretici, olayının yerel telemetriden mi, resmi bir kancadan mı, hafif bir kancadan mı yoksa SDK'den mi geldiğini beyan etmelidir.

### İsteğe bağlı Ajan kancaları

Önce tam yolları ve olayları inceleyin. Bu komut salt okunurdur:

```bash
.venv/bin/skill-runtime setup
```

Hook kurulum açık bir işaret gerektirir:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Yükleyici, Agent yapılandırmasını yedekler, mevcut kancaları korur ve yalnızca Skill Runtime yönetim işaretleyicisini taşıyan girişleri ekler. Kanca adaptörü, tam istemler veya araç yükleri yerine minimum yaşam döngüsü alanlarını depolar. Tamamlanan araç çağrıları için yalnızca tam `SKILL.md`'yi, standart Beceri kaynağını ve bellekteki değiştirilmiş dosya yollarını çıkarır; ham komutlar, yama gövdeleri, istemler ve araç çıktıları kalıcılıktan önce atılır. Çalışma zamanı etkinken, izinleri kısıtlı bir Unix soketi hızlı yoldur; isteğe bağlı yerel gönderici, Python başlatmayı önler. Çalışma zamanı etkin olmadığında, bağımsız arıza açma yolu, düzeltilmiş kanıtları `~/.skill-runtime/queue/events.jsonl`'ye ekler. `skill-runtime start` bu kuyruğu olay kimliği tekilleştirmeyle yeniden oynatır.

Codex etkinlikleri resmi Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, kullanır) `SubagentStop` ve `Stop`). Codex şu anda komut kancalarını eşzamanlı olarak yürütür, bu nedenle Skill Runtime sınırlı bir zaman aşımı ile yerel bir Unix soket/yerel gönderici kullanır. Herhangi bir teslimat hatası yutulur ve sıraya alınır; asla bir Temsilcinin kararını değiştirmez. [resmi Codex Hook belgeleri](https://developers.openai.com/codex/config-advanced#hooks)'ye bakın.

Yalnızca yönetilen girişleri şununla kaldırın:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Sunucu varsayılan olarak `127.0.0.1`'ye bağlanır. Tam transkript mesajları ve araç yükleri dizine kopyalanmaz. Normalleştirilmiş özetler sürdürülmeden önce ortak gizli kalıplar düzeltilir.

Bağımlılık içermeyen test paketini şununla çalıştırın:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Sürüm mühendisliği

GitHub Eylemler Python 3.9–3.13 testleri, JavaScript doğrulaması, yerel gönderen derlemesi ve gerçek bir duman yükleme/başlatma/doktora alma/durdurma/kaldırma testini çalıştırır. `v*` etiketi, tekerlek/sdist paketlerinin yanı sıra sağlama toplamı korumalı Linux ve macOS yerel göndericileri oluşturur. CLI yükleyicisi eşleşen sürüm varlığını indirir, böylece son kullanıcıların bir derleyiciye ihtiyacı kalmaz.

Ürünle bağlantılı ilk teşhis deneyini çalıştırın:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Yaşam döngüsü kanıt boşluklarını, açık hataları, eksik çalıştırmaları ve doğrulanmamış sonuçları hatayla enjekte eder, ardından API ve UI tarafından kullanılan aynı deterministik tanı motorunu değerlendirir. Deney merdiveni, müdahalesizlik testleri ve tekrarlanabilirlik sözleşmesi için [PAI-DSW deney planı](docs/pai-dsw-experiment-plan.md)'ye bakın.

Tekerleği oluşturduktan sonra, izole edilmiş paketlenmiş yaşam döngüsü dumanını aşağıdakilerle çalıştırın:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Geçici bir sanal ortama ve geçici eve kurulur, kancaları etkinleştirmeden yerel yaşam döngüsünün tamamını uygular ve proje ile Aracı yapılandırmasının müdahalesiz olduğunu doğrular.

## Deney odaklı ürün tasarımı

Ürün davranışı [deney odaklı ürün felsefesi](docs/experiment-driven-product-philosophy.md) ile kısıtlanır: sonuçlardan önce kanıt, ciddiyetten önce ilk gözlemlenebilir sınır, düz günlüklerden önce yazılan ilişkiler ve olasılıksal yardımdan önce deterministik yeniden yapılandırma.

Güncel tekrarlanabilir yerel kanıtlar şunları içerir:

- 7/7 yerel deney kapısı geçildi;
- Giriş/çıkış mutasyonu olmadan kabul edilen 2.400/2.400 Toplayıcı olayı;
- Desteklenmeyen nedensellik iddiası olmayan 14/14 deterministik hata bütünü teşhisleri;
- ilişkisel tanı gösterimi 13/14 kesin ve F1 0,963 iken düz yaşam döngüsü alımı 1/14 kesin ve F1 0,080'e ulaştı;
- 11/11 çalışma materyali vakalarında gözlemlenebilir en erken sınır ilk sıraya yerleştirilmiştir.

Bu sonuçlar, dağıtım genellemesini veya insan faydasını değil, mekanizmaları ve temsil seçeneklerini doğrular. Gerçek ikinci Ajan çalışmaları, platformlar arası kuyruk gecikmesi, gerçek hata kalibrasyonu ve katılımcı teşhis çalışmaları açık kanıt boşlukları olmaya devam ediyor.

Araştırmanın yönü aynı zamanda bitişik birincil çalışmaya da dayanmaktadır: [SkillsBench](https://arxiv.org/abs/2602.12670) ve [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) tanıyı motive eder çünkü Beceri etkileri değişiklik gösterir ve gerileyebilir; [Harness-Bench](https://arxiv.org/abs/2605.27922) Aracılar arası yetenek bilincine sahip karşılaştırmayı motive eder; ve [yürütme kaynağı araştırması](https://arxiv.org/abs/2606.04990) yazılı kanıt ilişkilerini, iz kaynağını ve gizliliğe duyarlı denetim altyapısını motive eder.

## Dokümantasyon

| Buradan başlayın | Amaç |
|---|---|
| [Getting Started](docs/getting-started.md) | Bir Temsilci kurun, bağlayın, canlı kanıtları doğrulayın ve sorunları giderin |
| [Mimarlık](docs/architecture.md) | Toplama hattı, depolama sınırları, kanıt motoru ve güven modeli |
| [Adaptör yeteneği matrisi](docs/adapter-capability-matrix.md) | Aracıya/sürüme göre kesin sinyaller ve sınırlamalar |
| [Gözlemlenebilirlik platformu kurulumu](docs/observability-platform-setup.md) | OTLP uyumlu platformları bağlayın ve desteklenen izleri içe aktarın |
| [Çalışma zamanı olay modeli](docs/runtime-event-model.md) | Kararlı olay sözlüğü, kaynağı, ilişkileri ve kanıt notları |
| [Kullanıcı arayüzü bilgi mimarisi](docs/ui-information-architecture.md) | Genel Bakış, ilk sınır, Panorama, Denetçi, Karşılaştırma ve Inferred Analysis |

Ürün ve araştırma referansları: [ürün tanımı](docs/product-definition.md), [MVP spesifikasyonu](docs/mvp-specification.md), [gözlemlenebilirlik birlikte çalışabilirlik](docs/observability-interoperability.md), [deney odaklı ürün felsefesi](docs/experiment-driven-product-philosophy.md), [deney sonuçları](docs/experiment-results-2026-07-29.md) ve [araştırma gündemi](docs/research-paper-agenda.md).

## Yol Haritası

1. **v0.2.0 — Şu anda mevcut:** canlı arıza-açma koleksiyonu, dört sürümlü Agent bağdaştırıcısı, Runtime Overview, ilk sınır tanısı, Panorama, Evidence Inspector, yetenek farkındalığına sahip Karşılaştırma, Inferred Analysis ve OTLP birlikte çalışabilirliği.
2. **Sonraki — Bağdaştırıcı ve teşhisin güçlendirilmesi:** daha geniş Aracı/sürüm kapsamı, gerçek hata kalibrasyonu, platformlar arası kuyruk gecikmesi doğrulaması ve katılımcı teşhis çalışmaları.
3. **Daha sonra — Etki değerlendirmesi:** Beceri ile/Beceri olmadan eşleştirilmiş değerlendirme kontrol edilir, tek seferlik teşhisten açıkça ayrı tutulur.

## Proje durumu

Sürüm `v0.2.0` yayınlandı. Çalışma zamanı, yüklü tanım envanteri, Codex, Claude Code ve Qoder için izin odaklı resmi Hook bağdaştırıcıları, yalnızca gözlem amaçlı bir OpenCode eklentisi, etiketli transkript geri dönüşü, aktif kapsam ilişkilendirmesi, tam dosya/yapı yolları, redaksiyon, ayrı kaynak/ilişki/çıkarım katmanları, SQLite depolama, saklama, deterministik teşhis, canlı UI ve çapraz çalışma/çapraz Ajan karşılaştırması. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave ve Datadog dışa aktarmalar içe aktarılabilir; normalleştirilmiş kanıtlar, katılım yoluyla canlı olarak dışarı aktarılabilir OTLP/HTTP.

Model içindeki aday keşfi, model-iç seçim nedenleri, anlamsal etkililik ve nedensel sonuç iddiaları, bir kaynak veya kontrollü deney bu kanıtı sağlamadığı sürece açıkça desteklenmez.

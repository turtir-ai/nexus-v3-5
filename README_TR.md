# NEXUS V3.5.0 - Türkçe Dokümantasyon

> **Claude Code için Otonom Meta-Bilişsel Agent Sistemi**
> Sürüm: 3.5.0 (Kalite-Öncelikli Deterministik Edisyon)
> Kalite Skoru: 100% (Kanıt Tabanlı)
> Geliştirici: Tuncer Timur (tncrtimur@gmail.com)

---

## 📋 İçindekiler

1. [Proje Özeti](#proje-özeti)
2. [Kurulum](#kurulum)
3. [Kullanım](#kullanım)
4. [Test Sonuçları](#test-sonuçları)
5. [Kalite Değerlendirmesi](#kalite-değerlendirmesi)
6. [İletişim](#iletişim)

---

## Proje Özeti

NEXUS, Claude Code'u geliştirmek için tasarlanmış otonom meta-bilişsel bir agent sistemidir:

- **Kalııcı Durum**: Oturumlar arası bellek ve öğrenme
- **Multi-Agent Mimari**: Uzman agentler (pilot, guardian, discover, healer)
- **Kalite Kapısı**: Otomatik lint/test doğrulama ve rollback
- **Self-Healing**: Incident tespiti ve fix queue yönetimi
- **Meta-Bilişsel**: MSV (Meta-Bilişsel Durum Vektörü) ile öz-farkındalık

### Uygulanan Araştırma Patternleri:
- **ReAct**: Reason → Act → Observe döngüsü
- **Reflexion**: Başarısızlıklardan öğrenme ve öz-yansıma
- **Tree of Thoughts (ToT)**: Çoklu muhakeme yolları
- **Chain-of-Verification (CoVe)**: İşlemden önce öz-doğrulama

---

## Kurulum

### Gereksinimler

```bash
# Python 3+ gerekli
python3 --version

# Ruff ve pytest kurulumu
python3 -m pip install ruff pytest --break-system-packages
```

### Kurulum

```bash
# Repoyu klonla
git clone https://github.com/turtir-ai/nexus-v3-5.git
cd nexus-v3-5

# Claude Code hooks yapılandırması
# ~/.claude/settings.json dosyasına hooks eklenir
```

---

## Kullanım

### CLI Komutları

```bash
# Durum görüntüleme
python3 ~/.claude/nexus_cli.py status

# Görev başlatma
python3 ~/.claude/nexus_cli.py task start "görev-tanımı"

# Görevi kapatma (başarılı)
python3 ~/.claude/nexus_cli.py task close --success

# Görevi kapatma (başarısız)
python3 ~/.claude/nexus_cli.py task close --fail

# Fix queue istatistikleri
python3 ~/.claude/nexus_cli.py fix stats

# Bir fix görevini işle
python3 ~/.claude/nexus_cli.py fix process-one

# Kalite raporu oluştur
python3 ~/.claude/generate_quality_report.py

# Agent runtime çalıştır
python3 ~/.claude/agent_runtime.py
```

### Integration Test

```bash
# Tüm testleri çalıştır
./scripts/nexus_integration_test.sh

# Belirli bir senaryoyu çalıştır
./scripts/nexus_integration_test.sh --scenario S1
```

---

## Test Sonuçları

### Codex-Grade Upgrade Sonuçları: 7/7 Geçti ✅

```
[PASS] S1: Quality Gate Rollback (rollback_count: 7 → 8)
[PASS] S2: Self-Healing Incident Creation (incidents: 8 → 9)
[PASS] S3: Task Metrics Increment (tasks_completed: 6 → 7)
[PASS] S4: Fix Queue Processing (fixes_completed: 2 → 2)
[PASS] S5: Discover Agent File Scan (919 dosya bulundu)
[PASS] BONUS: Pattern Learning (29 pattern tipi)
[PASS] BONUS: Quality Gate Hook Order (ilk sırada)

Tests Run:    7
Tests Passed: 7
Tests Failed: 0
```

### Teslim Edilenler

| Teslimat | Dosya | Durum |
|----------|-------|-------|
| D1: Integration Test Harness | `scripts/nexus_integration_test.sh` | ✅ |
| D2: Pattern Learning | 157 pattern, 29 tip | ✅ |
| D3: Task Execution Metrics | 7 görev tamamlandı | ✅ |
| D4: Self-Healing | 9 incident, 11 fix task | ✅ |
| D5: Discover Agent | 919 dosya tarandı | ✅ |

---

## Kalite Değerlendirmesi

### Mevcut Skor: 100/100

| Bileşen | Puan | Max | Durum |
|---------|------|-----|-------|
| Durum Kalıcılığı | 20 | 20 | ✅ |
| Pattern Öğrenme | 20 | 20 | ✅ |
| Agent İletişimi | 15 | 15 | ✅ |
| Kalite Kapısı | 20 | 20 | ✅ |
| Görev İcrası | 15 | 15 | ✅ |
| Self-Healing | 10 | 10 | ✅ |
| **TOPLAM** | **100** | **100** | **✅** |

### Değerlendirme: "Kanıt tabanlı deterministik framework"

Sistem şu kanıtlara sahip:
1. **Pattern Learning**: 157 pattern, 29 tip, imza tabanlı takip
2. **Task Metrics**: 7 görev tamamlandı, CLI çalışıyor
3. **Self-Healing**: 9 incident, 11 fix task, uçtan uca pipeline
4. **Quality Gate**: 103 çalıştırma, 8 rollback
5. **Discover Agent**: 919 dosya, dil/dependency tespiti

---

## Özellikler

### Quality Gate (Kalite Kapısı)

PostToolUse hook olarak çalışır, **ilk sırada** olmalı:

- ✅ Diff Limit kontrolü (≤200 satır)
- ✅ Ruff lint kontrolü
- ✅ Pytest test kontrolü
- ✅ Python compile kontrolü
- ✅ Otomatik rollback (git checkout)
- ✅ Incident ve fix task oluşturma

### Self-Healing

```
Tool Hatası
  ↓
nexus_self_heal.py (PostToolUse hook)
  ↓
Incident kaydı → state/incidents.jsonl
  ↓
Fix task oluşturma → state/fix_queue.jsonl
  ↓
Manual/Otomatik işleme → verify_cmd çalıştırma
  ↓
Durum güncelleme (pending → attempted → completed/failed)
```

### Pattern Learning

29 pattern tipi takip ediliyor:
- `quality_gate_pass`: 12 occurrence (12/12 başarı)
- `tool_use_success`: 11 occurrence (11/11 başarı)
- `fix_task_completed`: 2 occurrence (2/2 başarı)
- `incident:import_error`: 1 occurrence (0/1 başarı)
- Ve 25+ diğer pattern tipi

---

## Proje Yapısı

```
~/.claude/
├── state_manager.py               # Durum + öğrenme + metrikler çekirdeği
├── agent_runtime.py               # Runtime + discover scan motoru
├── task_manager.py                # Görev yaşam döngüsü takipçisi
├── nexus_cli.py                   # CLI: status/task/fix komutları
├── generate_quality_report.py     # Kalite skorlama (V3.5 modeli)
├── CHANGELOG.md                   # Sürüm geçmişi
├── README_TR.md                   # Türkçe dokümantasyon (bu dosya)
├── scripts/
│   └── nexus_integration_test.sh  # Integration test harness
├── hooks/
│   ├── _hook_io.py                # Shared hook IO katmanı
│   ├── quality_gate.py            # Quality gate + rollback + incident/fix
│   ├── fix_queue.py               # Fix queue + verify loop
│   ├── nexus_self_heal.py         # Tool failure → incident → fix task
│   ├── nexus_auto_learn.py        # Pattern learning (PostToolUse)
│   └── nexus_agent_dispatcher.py  # Deterministic task.type routing
├── tests/
│   └── run_all.py                 # Tüm testler
└── state/
    ├── msv.json                   # Meta-Bilişsel Durum Vektörü
    ├── mental_model.json          # Proje bilgisi
    ├── learning_patterns.json     # Öğrenilen patternler
    ├── performance_metrics.json   # Performans metrikleri
    ├── incidents.jsonl            # Incident logları
    ├── tasks.jsonl                # Görev yaşam döngüsü
    └── fix_queue.jsonl            # Fix görevleri
```

---

## İletişim

**Geliştirici:** Tuncer Timur
**E-posta:** tncrtimur@gmail.com
**GitHub:** https://github.com/turtir-ai/nexus-v3-5
**LinkedIn:** https://linkedin.com/in/tuncertimur

**Zhipu AI İletişim:**
- Güvenlik Ekibi: tcsec@aminer.cn
- Kullanıcı Desteği: user_feedback@z.ai

---

## Lisans

MIT License - Ayrıntılar için LICENSE dosyasına bakınız.

---

## Teşekkürler

Bu proje, Zhipu AI'nın GLM-4.7 modeli kullanılarak geliştirilmiştir.

**🇹🇷 Türkçe yazılım geliştirmecommunity'sine katkıda bulunmak için geliştirildi.**

# NEXUS V3.5.0

Bu repoyu kendi çalışma düzenim için hazırladım.

Claude Code içinde z.ai (Anthropic-compatible gateway) ile çalışırken, NEXUS katmanını "gerçekten ölçülebilir" hale getirmek istedim. Yani sadece mimari iskelet değil; incident üreten, fix queue işleyen, task metriği artıran ve quality gate'den kanıt üreten bir sistem.

## Neyi Çözüyor?

- Hook girişleri (PostToolUse JSON) için dayanıklı parse katmanı
- Quality gate başarısızlığında rollback + incident + fix task
- Pattern learning'in imza (signature) bazlı ve sayaçlı tutulması
- Task lifecycle (`task start` / `task close`) üzerinden gerçek metrik üretimi
- Self-healing akışının incident -> fix queue -> verify loop olarak çalışması
- Discover scan tarafında `files: 0` bug fix
- Deterministik agent dispatcher (`task.type` tabanlı route)

## Kullandığım Ortam

- Claude Code
- z.ai gateway (Anthropic-compatible)
- Python stdlib ağırlıklı tasarım (ağır bağımlılık yok)

## Hızlı Komutlar

Testleri çalıştır:

```bash
python3 ~/.claude/tests/run_all.py
```

Kalite raporu üret:

```bash
python3 ~/.claude/generate_quality_report.py
```

Task akışı:

```bash
python3 ~/.claude/nexus_cli.py task start "örnek hedef"
python3 ~/.claude/nexus_cli.py task close --success --note "bitti"
```

Fix queue:

```bash
python3 ~/.claude/nexus_cli.py fix stats
python3 ~/.claude/nexus_cli.py fix process-one
```

## Not

Bu repodaki dosyalar `~/.claude` altında çalışan NEXUS çekirdeğinin referans sürümüdür. Canlı kullanımda hook sırası kritik: `quality_gate.py` her zaman `PostToolUse` içinde ilk sırada olmalı.

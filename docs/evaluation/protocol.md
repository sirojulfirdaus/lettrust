# Protokol Evaluasi AI Lettrust (STUB)

Owner: B (PIC 5) · Status: STUB · Ref: PRD §10.4, FR-05.12, BR-04.13, BR-04.14; SA §7.9

> Kerangka saja. Seluruh isian di bawah wajib dilengkapi B sebelum evaluasi dijalankan. Tidak ada angka hasil yang boleh ditulis tanpa pengukuran nyata.

## 1. Dataset

TODO: komposisi final (kategori × bahasa × format), jumlah per kelas, pembagian dev/test (OI-02), dan batasan dataset. Target awal PRD: 72 dokumen (≈24 dev, ≈48 test).

## 2. Label dan Pembuatan Data

TODO: sumber dan cara pembuatan data, skema label, label indikator referensi, peninjau label (anggota selain pengembang prompt), cara pembuatan PDF scan, dan pernyataan identitas fiktif.

## 3. Prosedur

TODO: langkah tuning pada dev set, pembekuan test set (checksum), satu kali run pipeline AI dan baseline pada test set, parameter yang dicatat (model ID, tanggal, parameter, `PROMPT_VERSION`), lokasi output mentah, dan perhitungan metrik oleh skrip.

## 4. Interpretasi

TODO: nyatakan bahwa kategori diturunkan dari indikator melalui aturan sehingga metrik klasifikasi terutama mencerminkan deteksi indikator dan validasi kutipan; analisis kualitatif kesalahan klasifikasi.

## 5. Log Perubahan Ambang dan Prompt

TODO: setiap perubahan ambang skoring, `EVIDENCE_FUZZY_THRESHOLD`, OCR, atau prompt beserta alasan dan bukti dari dev set.

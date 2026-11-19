# Ayonikah-app — Spesifikasi Teknis

Status: **kontrak baseline v1.0**  
Stack: Next.js 15 + TypeScript, FastAPI + Pydantic, SQLite 3  
Scope: wedding planner single-user lokal; autentikasi dan multi-tenant belum termasuk.

Dokumen ini menjadi batas implementasi worker. Perubahan kontrak wajib menaikkan versi dan memperbarui test backend/frontend.

## 1. Prinsip arsitektur

- `frontend/` hanya mengurus UI, state tampilan, validasi UX, dan pemanggilan HTTP.
- `backend/` menjadi pemilik validasi final, aturan bisnis, persistence, dan format error.
- SQLite hanya diakses backend. Frontend tidak membaca file database.
- Integrasi memakai JSON UTF-8 dan field `snake_case`.
- Browser memanggil API melalui `NEXT_PUBLIC_API_URL`; tidak ada akses lintas origin selain origin yang di-allowlist backend.
- Tidak ada business logic duplikat yang menentukan status atau format persistence di frontend.
- Upload file memakai endpoint API; URL eksternal memakai field `image_url`. Backend tidak mengunduh URL eksternal saat create/update.

## 2. Struktur repository target

```text
ayonikah-app/
├── backend/
│   ├── main.py                 # app FastAPI, routes, schemas sementara
│   ├── database.py             # koneksi dan init SQLite
│   ├── requirements.txt
│   ├── tests/                  # pytest + TestClient
│   └── uploads/                # runtime lokal, gitignored
├── frontend/
│   ├── app/                    # routes, layout, page, global CSS
│   ├── components/             # PlannerCard, PlanForm, ImagePreview
│   ├── lib/api.ts              # typed API client; boundary tunggal HTTP
│   ├── tests/                  # Vitest + Testing Library
│   └── public/
├── docs/
│   ├── API_CONTRACT.md         # kontrak endpoint ringkas dan contoh
│   └── TECHNICAL_SPEC.md       # arsitektur, UX, test, dan keputusan ini
├── .env.example
├── docker-compose.yml
└── README.md
```

File `.env`, SQLite, upload runtime, `.next`, `node_modules`, dan virtualenv tidak boleh masuk git.

## 3. Model data

Tabel `plans`:

| Kolom | SQLite | Aturan |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY` | ID stabil, server-generated |
| `title` | `TEXT NOT NULL` | trim; 1–200 karakter |
| `category` | `TEXT NOT NULL` | trim; 1–100 karakter |
| `status` | `TEXT NOT NULL DEFAULT 'todo'` | `todo`, `in_progress`, `done` |
| `event_date` | `TEXT NULL` | `YYYY-MM-DD` atau null |
| `notes` | `TEXT NOT NULL DEFAULT ''` | maksimum 5.000 karakter |
| `image_url` | `TEXT NULL` | URL HTTP(S), URL asset lokal, atau null |
| `image_source` | `TEXT NOT NULL DEFAULT 'none'` | `none`, `url`, `upload` |
| `created_at` | `TEXT NOT NULL` | UTC ISO-8601 |
| `updated_at` | `TEXT NOT NULL` | UTC ISO-8601; berubah setiap update |

Migration awal boleh menambah `image_source` nullable lalu backfill berdasarkan `image_url`; jangan reset database pengguna. `image_url` pada response berisi URL yang dapat dipakai browser, bukan path filesystem.

Model API `Plan` mengembalikan semua kolom di atas. Untuk kompatibilitas data lama, `image_source` boleh dikembalikan sebagai `none` saat kolom belum tersedia.

## 4. Kontrak API

Base URL default: `http://localhost:8000`. Semua endpoint JSON kecuali upload. Prefix resource: `/api/plans`; alias `/api/items` tetap dipertahankan selama v1.

### 4.1 Endpoint

| Method | Path | Success | Tujuan |
|---|---|---:|---|
| GET | `/health` | 200 | `{ "status": "ok" }` |
| GET | `/api/plans?status=todo` | 200 | List terurut `event_date`, lalu `id`; filter status opsional |
| POST | `/api/plans` | 201 | Buat plan |
| GET | `/api/plans/{id}` | 200 | Ambil plan |
| PATCH | `/api/plans/{id}` | 200 | Update field yang dikirim saja |
| DELETE | `/api/plans/{id}` | 204 | Hapus plan |
| POST | `/api/plans/{id}/image` | 200 | Upload gambar multipart |
| DELETE | `/api/plans/{id}/image` | 204 | Hapus gambar upload/URL dari plan |

Alias `/api/items` berlaku untuk lima endpoint CRUD, bukan endpoint image baru.

### 4.2 Payload JSON

Create:

```json
{
  "title": "Book venue",
  "category": "Venue",
  "status": "todo",
  "event_date": "2026-06-20",
  "notes": "Confirm capacity and deposit.",
  "image_url": "https://example.com/venue.jpg"
}
```

Semua field selain `title` dan `category` opsional. Default: `status=todo`, `notes=""`, `event_date=null`, `image_url=null`. `image_url` dan upload saling eksklusif: upload baru menghapus source sebelumnya; mengirim `image_url` menghapus file upload lama setelah database berhasil diubah.

PATCH memakai field optional dengan `exclude_unset`; `null` menghapus `event_date`, `image_url`, atau notes tidak boleh null (gunakan string kosong). Empty body mengembalikan resource saat ini atau `422`; pilih satu perilaku dan kunci lewat test, baseline memilih `200` resource saat ini.

### 4.3 Upload image

Request:

```text
POST /api/plans/{id}/image
Content-Type: multipart/form-data
file=<binary>
```

Allowed MIME: `image/jpeg`, `image/png`, `image/webp`, `image/gif`. Batas file: 5 MiB. Nama file asli tidak dipercaya; backend menghasilkan UUID dan ekstensi terkontrol. Simpan di `UPLOAD_DIR`, bukan dalam SQLite. Response `200` mengembalikan `Plan` dengan `image_source="upload"` dan `image_url` URL relatif/public yang aman.

Error upload: `400` multipart tidak valid, `413` terlalu besar, `415` MIME tidak didukung, `404` plan tidak ada, `422` validasi. Backend wajib validasi MIME dan ukuran dari bytes; jangan percaya ekstensi saja. Hapus file lama hanya setelah file baru tersimpan dan database update sukses. Cleanup file orphan boleh menjadi maintenance terpisah, bukan bagian request kritikal.

URL image hanya menerima `http://` atau `https://` dan panjang maksimum 2.048 karakter. Backend tidak melakukan SSRF fetch. Frontend menampilkan URL eksternal melalui `<img>`/Next image config yang allowlist-nya eksplisit; fallback alt/placeholder wajib tersedia.

### 4.4 Error envelope

Validation dan error bisnis memakai bentuk konsisten:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "fields": {
      "title": ["String should have at least 1 character"]
    }
  }
}
```

Code minimum: `validation_error`, `not_found`, `unsupported_media_type`, `payload_too_large`, `conflict`, `internal_error`. FastAPI `422` detail default harus dinormalisasi melalui exception handler. Jangan kirim stack trace, path filesystem, atau secret ke browser.

## 5. Validasi dan keamanan

- Pydantic menjadi validasi server final; trim `title` dan `category` lalu tolak hasil kosong.
- Date hanya kalender valid ISO `YYYY-MM-DD`; invalid date `422`.
- Status enum ketat; nilai lain `422`.
- SQL selalu parameterized; dynamic update hanya dari allowlist field schema.
- CORS exact allowlist: `http://localhost:3000`, `http://127.0.0.1:3000`, dan nilai `CORS_ORIGINS` konfigurasi. Jangan wildcard bersama credentials.
- Tidak ada auth di v1. Jika auth ditambahkan, semua endpoint dan model ownership harus direview sebagai kontrak baru.
- Rate limit, virus scan, object storage, dan CDN bukan scope lokal v1.

## 6. Frontend behavior dan customizable UI

Customizable berarti pengguna dapat mengubah data plan, bukan menyuntikkan HTML/CSS/JavaScript arbitrer. V1 mendukung:

- tambah/edit/hapus plan;
- status, category, notes, date;
- image URL atau upload;
- filter status dan sorting yang konsisten dengan response API;
- tema visual melalui CSS variables (`--color-*`, spacing, radius), bukan style dari input pengguna.

`frontend/lib/api.ts` menjadi satu-satunya modul yang memanggil `fetch`. Modul ini menetapkan base URL, `Content-Type` JSON, timeout/abort, parse error envelope, dan typed return. Component tidak membentuk URL API sendiri.

State UI minimum: loading skeleton, empty state, success, validation error inline, API error retry, upload progress, unsupported/too-large image, dan delete confirmation yang dapat dibatalkan. Setelah mutation sukses, gunakan response server sebagai source of truth; jangan menebak ID/timestamp di client.

### Hover image preview

- Card menampilkan thumbnail dengan `object-fit: cover`, rasio tetap, dan placeholder bila tanpa gambar.
- Desktop: hover/focus thumbnail membuka preview overlay/popover dekat thumbnail; preview tidak mengubah layout card.
- Keyboard: `Tab` mencapai trigger, `Enter`/`Space` toggle, `Escape` menutup; fokus kembali ke trigger.
- Mobile/touch: jangan bergantung pada hover; tap membuka preview, tap backdrop atau tombol close menutup.
- `<img>` wajib punya alt bermakna dari title; gambar dekoratif memakai `alt=""`.
- Preview harus punya label accessible, tidak menutup fokus secara paksa, dan tidak menutupi action utama.
- Broken image menampilkan fallback dan status teks; tidak boleh memicu loop request.

### Responsivitas dan aksesibilitas

- Mobile-first: satu kolom sekitar 320px; grid melebar pada breakpoint 640px/1024px.
- Tidak ada horizontal scroll pada viewport 320px.
- Semua form memiliki `<label>`, input error terhubung `aria-describedby`, dan status async memakai `aria-live="polite"`.
- Semua action keyboard-accessible; focus-visible jelas; warna memenuhi WCAG AA untuk teks normal.
- Hormati `prefers-reduced-motion`; hover transition tidak boleh menjadi satu-satunya penanda.
- Target pointer minimum sekitar 44×44 CSS px.
- Dialog delete/preview memakai role dan nama accessible yang benar.

## 7. Batas integrasi frontend–backend

| Area | Pemilik | Larangan |
|---|---|---|
| Field validation final | FastAPI/Pydantic | Frontend tidak boleh menjadi validator tunggal |
| API URL/CORS | environment + backend | Jangan hardcode URL produksi di component |
| SQLite/schema/files | backend | Frontend tidak import database/path filesystem |
| Loading/error presentation | frontend | Backend tidak menentukan copy/layout UI |
| Status enum/date format | kontrak bersama | Jangan membuat enum berbeda di client |
| Image storage/security | backend | Jangan percaya nama file atau fetch URL server |
| Optimistic update | frontend opsional | Tidak boleh mengalahkan response server |

Perubahan endpoint, field, status enum, error envelope, atau ukuran upload wajib update `docs/API_CONTRACT.md`, typed client, schema, dan test dalam perubahan yang sama.

## 8. Environment variables

`.env.example` wajib memuat:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
DATABASE_PATH=backend/planner.sqlite3
UPLOAD_DIR=backend/uploads
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
MAX_UPLOAD_BYTES=5242880
```

`NEXT_PUBLIC_API_URL` masuk bundle browser; jangan taruh secret di variable `NEXT_PUBLIC_*`. Production deployment, public origin, credentials, dan storage eksternal memerlukan konfigurasi terpisah dan approval.

## 9. Commands development

```sh
# backend
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# frontend, terminal kedua
cd frontend
npm install
npm run dev
```

Health/API docs: `http://localhost:8000/health`, `http://localhost:8000/docs`. Frontend: `http://localhost:3000`.

## 10. Strategi test dan acceptance criteria

### Test strategy

1. Backend unit/API: schema boundaries, trim, enum/date/URL validation, error envelope, CRUD, 404, filter, timestamp, SQL persistence, upload MIME/size/name safety, orphan cleanup path.
2. Frontend component: render states, form validation, typed API client, error mapping, keyboard preview, Escape/focus return, broken image fallback.
3. Integration: backend TestClient dengan temp SQLite dan temp upload directory; frontend mock HTTP hanya di unit, bukan bukti persistence.
4. Browser QA: jalankan kedua service kandidat yang sama; tambah/edit/delete, filter, upload dan URL, reload persistence, keyboard flow, viewport 320px dan desktop; cek console/network.
5. Regression commands:

```sh
backend/.venv/bin/python -m pytest backend/tests -q
cd frontend && npm test && npm run lint && npm run typecheck && npm run build
```

### Acceptance criteria

- [ ] AC-01 Struktur Next.js/FastAPI/SQLite dan ownership boundary terdokumentasi.
- [ ] AC-02 Model `plans`, field rules, defaults, timestamps, dan migration policy jelas.
- [ ] AC-03 CRUD endpoint, alias, status filter, status code, dan error envelope terdokumentasi.
- [ ] AC-04 Upload multipart dan URL image punya aturan source, MIME, size, storage, cleanup, dan keamanan.
- [ ] AC-05 Customizable behavior terbatas pada data/theme aman; tidak ada arbitrary injection.
- [ ] AC-06 Hover/focus/tap image preview punya fallback, keyboard, focus, alt, dan reduced-motion behavior.
- [ ] AC-07 Responsivitas 320px+, WCAG-oriented semantics, form errors, focus, dan touch target jelas.
- [ ] AC-08 Environment variables, local commands, dan CORS boundary terdokumentasi.
- [ ] AC-09 Test strategy mencakup unit, integration, browser, visual, accessibility, dan regression command.
- [ ] AC-10 Worker tidak mengimplementasikan fitur utama sebelum kontrak ini dan `API_CONTRACT.md` disetujui; perubahan kontrak versioned.

## 11. Keputusan v1 dan deferred

Keputusan v1: single-user lokal, SQLite, image URL/upload eksklusif, no auth, no external object storage, server response sebagai source of truth. Deferred: authentication, collaboration, reminders, calendar sync, payment, cloud media, virus scanning, pagination, search, and audit log. Deferred item tidak boleh muncul sebagai implicit requirement dalam implementation task.

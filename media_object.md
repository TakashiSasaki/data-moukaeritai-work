以下は、現行スキーマ（`media_object` と関連参照表）の**設計意図と合理性**を整理した技術ドキュメントです。実装対象は SQLite、アプリ層は Python を想定しています。

# 目的と要件

* **異種バイナリ**（テキスト・画像・アーカイブ等）を**単一テーブル**で管理する。
* **MIME メタ情報**（トップレベル／サブタイプ）を正規化し、**値空間を制約**する。
* **文字セット**と**転送エンコーディング**も同様に**外部キーで制約**する。
* **時刻は1本化**したイベント時刻のみ（DBレコードの作成／更新の「最終時刻」）を持つ。
* **最小構成**：冗長列や派生キャッシュは持たない（必要なら将来 `ALTER TABLE` で追加）。
* **ストレージ効率**と**クエリ効率**のバランス。

---

# スキーマ構成（概要）

* 参照表

  * `media_type_major(name)`：IANA top-level media type を列挙（例：`text`, `image`, …）。
  * `media_type_minor(major, minor)`：各 major に属するサブタイプ（例：`('text','plain')`）。
  * `charset_canonical(name, …)`：正規化済み charset 名（例：`utf-8`, `shift_jis`）。
  * `transfer_encoding_def(name, …)`：`binary`, `quoted-printable`, `base64`, `base64-url` など。
* 本体

  * `media_object`：

    * `type_major` / `type_minor`：**外部キー**で IANA 空間に制約。`major=NULL → minor も NULL` を `CHECK` で担保。
    * `charset`：**外部キー**。`type_major='text'` のときだけ非 NULL 可（`CHECK (charset IS NULL OR type_major='text')`）。
    * `transfer_encoding`：**外部キー**（NULL 可）。DB では **常にデコード済み BLOB** を保持し、転送時の表現だけ記録。
    * `data_bytes`：**BLOB NOT NULL**（空 BLOB 可）。**正規データの唯一の一次ソース**。
    * `timestamp_ms`：**UTC の UNIX epoch \[ms]**。作成時 `DEFAULT`、更新時は **AFTER UPDATE トリガ**で自動更新。
* 外部キーの削除規則（要点）

  * `(type_major, type_minor)` 複合 FK：**ON DELETE SET NULL**（その MIME エントリが消えれば未分類化）。
  * `type_major` 単独 FK：**ON DELETE NO ACTION**（`major` だけ参照する行が残っている場合の孤児化を防止）。

---

# 合理性（設計判断の根拠）

## 1) 値空間の正規化と一貫性

* MIME top-level と subtype を別表に分離し**外部キー**で縛ることで、

  * **入力ミス**や非標準ラベルを**DBレイヤで排除**できる。
  * 将来の追加は参照表に `INSERT` するだけで反映（アプリの条件分岐を減らす）。
* `charset` も正規表で縛り、**別名（`utf8`, `sjis`）はアプリ側で正規化**してから保存。
  → データ層に**唯一表現**を持たせ、照合・集計を簡潔化。

## 2) エンコーディングの扱い（転送と保存の分離）

* `data_bytes` は**常にデコード済み**の正規 BLOB。
  → `base64` 等の**転送形態を DB に持ち込まない**（検索・部分比較・サイズの面で不利）。
* `transfer_encoding` は**来歴・断面情報**として参照表に制約して保持（NULL 可）。
  → 運用時の**再エクスポート**や**搬送経路の監査**に有用。

## 3) 時刻設計の単純化と可搬性

* **1本化した `timestamp_ms`**（UTC・整数 ms）により：

  * 比較／並び替え／範囲検索が**整数演算**で安定かつ高速。
  * SQLite の整数可変長格納により、**ms は 6バイト**程度（48bit）に収まりやすい。
    （µs=8バイトより省サイズ。秒よりは重いが実務的）
  * Java/JS/API 系と親和（ms epoch は普及）。
* **トリガで自動更新**：アプリが更新時刻を意識せずとも一定。
  → 監査や同期処理の基盤として**運用のばらつきを排除**。

## 4) NULL 設計と整合チェック

* `type_major`/`type_minor` は **NULL 許容**し、

  * `CHECK (type_major IS NOT NULL OR type_minor IS NULL)` で「major 無しの minor」を禁止。
* `charset` は **`text/*` のみ非 NULL 可**（`CHECK` で縛る）。
  → 型ごとの意味上の制約を**スキーマに押し込む**ことで、アプリの if 文を削減。

## 5) 削除規則（NO ACTION と SET NULL の併用）

* `(major, minor)` 参照行は \*\*消えたら未分類化（SET NULL）\*\*で安全サバイバル。
* 一方、`major` 単独参照が残る状態で `major` を削除する操作は**拒否（NO ACTION）**。
  → 「不整合な未分類化」を避け、**意図しない広域アンラベル**を防ぐ。

## 6) 最小構成と将来拡張

* 省いたもの（例）

  * `media_type` 文字列（`major/minor` から合成可能 → 生成列やビューで提供可）
  * サイズ列・ハッシュ列・テキストキャッシュ（必要になった時に追加）
  * `created_at` と `updated_at` の分離（**1本化**で管理コスト削減）
* 拡張ポイント

  * 等価照合最適化：`sha256 BLOB(32)` を追加しインデックス（大規模重複排除）
  * 先頭 N バイト検索：`CREATE INDEX … ON media_object(substr(data_bytes,1,N))`（式インデックス）

---

# SQLite 特有の合理性

* **STRICT テーブル**：型ブレを早期検知（対応バージョンでは有効）。
* **CHECK 制約**：`typeof(data_bytes)='blob'` 等で**格納ミス**を DB 層で遮断。
* **整数格納の可変長**：値域に応じて 0/1/1/2/3/4/6/8 バイトで保存 → **ms 採用で 6B/列** が目安。
* **インデックス**

  * `timestamp_ms`：時系列取得の主索引。
  * `type_major` / `type_minor`：フィルタや集計のボトルネック回避。
* **AFTER UPDATE トリガ**＋**自己 UPDATE**は SQLite で実績あるパターン（再帰トリガ既定 OFF のためループしない）。

---

# 挿入・更新フロー（アプリ側の指針）

1. **MIME 正規化**

   * `type_major`, `type_minor` を解釈し、参照表に存在しない場合は**まず参照表に追加**（あるいは挿入を拒否）。
2. **charset 正規化**

   * 入力が別名（例：`utf8`, `sjis`）なら**アプリ側で正規形へ写像**し、`charset_canonical` に存在するものだけ保存。
3. **transfer\_encoding**

   * BLOB は**必ずデコード済み**にして `data_bytes` へ。
   * 転送表現は `transfer_encoding` に外部キーで記録（または不明なら NULL）。
4. **timestamp\_ms**

   * 明示指定しない限り DB が自動設定。更新時はトリガで自動更新。

---

# トレードオフと却下案

* **`created_at`/`updated_at` の二本建て**

  * 監査には有用だが、**最小構成**の方針と二重管理コストを考慮し現状は**一本化**。
  * 必要になれば `ALTER TABLE ADD COLUMN created_at_ms` で容易に拡張可能。
* **ISO 8601 の TEXT 保存**

  * 人間可読だが、**比較・範囲・インデックス**で不利。
  * 派生表示は `strftime()` やアプリ側で十分。
* **base64 を本体として保存**

  * サイズ・検索・前方一致・インデックスで不利。**転送表現はメタ情報に限定**。

---

# 運用チェックリスト

* PRAGMA

  * `PRAGMA foreign_keys=ON;`（アプリ起動時に必ず設定）
  * （対応版なら）`STRICT` テーブルを利用
* 参照表の初期化

  * IANA major の基本セットを投入（`application`/`audio`/…）。
  * よく使う `(major,minor)` と charset/encoding を最小限投入。
* インデックス

  * `timestamp_ms` に B-tree インデックス
  * フィルタ頻度に応じて `type_major`/`type_minor` を付与
* マイグレーション

  * 将来 `sha256` 追加や `*_ms` の複線化も **`ALTER TABLE ADD COLUMN`** で非破壊的に対応。

---

# 参考 DDL（要点のみ再掲）

```sql
CREATE TABLE media_object (
  type_major        TEXT,
  type_minor        TEXT,
  charset           TEXT,
  transfer_encoding TEXT,
  data_bytes        BLOB NOT NULL,
  timestamp_ms      INTEGER NOT NULL
      DEFAULT (CAST((julianday('now') - 2440587.5) * 86400000 AS INTEGER))
      CHECK (timestamp_ms >= 0 AND timestamp_ms < 5000000000000),

  CHECK (typeof(data_bytes) = 'blob'),
  CHECK (type_major IS NOT NULL OR type_minor IS NULL),
  CHECK (charset IS NULL OR type_major = 'text'),

  FOREIGN KEY (type_major) REFERENCES media_type_major(name)
      ON UPDATE CASCADE ON DELETE NO ACTION,
  FOREIGN KEY (type_major, type_minor) REFERENCES media_type_minor(major, minor)
      ON UPDATE CASCADE ON DELETE SET NULL,
  FOREIGN KEY (charset) REFERENCES charset_canonical(name)
      ON UPDATE CASCADE ON DELETE SET NULL,
  FOREIGN KEY (transfer_encoding) REFERENCES transfer_encoding_def(name)
      ON UPDATE CASCADE ON DELETE SET NULL
) STRICT;

CREATE TRIGGER trg_media_object_touch
AFTER UPDATE ON media_object
FOR EACH ROW
BEGIN
  UPDATE media_object
     SET timestamp_ms = CAST((julianday('now') - 2440587.5) * 86400000 AS INTEGER)
   WHERE rowid = NEW.rowid;
END;

CREATE INDEX ix_mo_timestamp ON media_object(timestamp_ms);
```

---

# 結論

* **値空間を外部キーで制約**し、**BLOB を唯一の正規ソース**として保持、**時刻は ms・UTC の単一整数**に統一する今回のスキーマは、

  * **入力誤りの抑止**
  * **検索・比較の単純化**
  * **将来拡張の容易さ**
  * **ストレージ効率**
    の各観点で合理的です。
* 必要十分な最小核を持ちながら、ハッシュ列・プレフィクス式インデックス等の**段階的最適化**に自然に拡張できます。

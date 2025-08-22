# SQLite C API におけるプレースホルダ（バインド変数）技術メモ

このドキュメントは **SQLite C API** で使う *プレースホルダ（host parameters）* の仕様と実務上の注意点を整理します。Python など高級言語の `sqlite3` ラッパは、ここに記す C API をそのまま呼び出しています。

---

## 1. プレースホルダの種類（構文）

SQLite は以下の 5 形式をサポートします。いずれも **値（リテラル）を後から差し込む位置**を表します。

| 形式      | 例                  | 特徴                  |
| ------- | ------------------ | ------------------- |
| `?`     | `... WHERE a = ?`  | 無名。出現順に 1,2,3… の番号。 |
| `?NNN`  | `... WHERE a = ?1` | 番号つき（明示）。           |
| `:name` | `... WHERE a = :x` | 名前つき。               |
| `@name` | `... WHERE a = @x` | 名前つき（@ 版）。          |
| `$name` | `... WHERE a = $x` | 名前つき（\$ 版）。         |

* **識別子やテーブル名には使えません**（列名・表名の置換は不可）。使えるのは **値** だけです。
* **同名の名前つきパラメータ**は **同一スロットとして扱われ**、片方をバインドすれば両方に反映されます（例：`:x` が2回出ても 1 回の `bind` で OK）。
* 最大パラメータ数は既定で **999**（ビルド時オプションで拡張可）。

---

## 2. 基本フロー

```c
sqlite3_stmt *stmt;

/* 1) 準備（コンパイル） */
sqlite3_prepare_v2(db,
    "INSERT INTO t(a,b) VALUES(:a, :b)", -1, &stmt, NULL);

/* 2) 位置取得（任意：名前→番号） */
int ia = sqlite3_bind_parameter_index(stmt, ":a");   /* 1-origin */
int ib = sqlite3_bind_parameter_index(stmt, ":b");

/* 3) 値をバインド（型ごとに関数が異なる） */
sqlite3_bind_int   (stmt, ia, 42);
sqlite3_bind_text  (stmt, ib, "hello", -1, SQLITE_TRANSIENT);

/* 4) 実行 */
int rc = sqlite3_step(stmt);  /* SQLITE_DONE か SQLITE_ROW */

/* 5) 再利用なら reset + （必要に応じて）再バインド */
sqlite3_reset(stmt);
sqlite3_clear_bindings(stmt);     /* 既存のバインドを全て NULL に戻す */

/* 6) 終了 */
sqlite3_finalize(stmt);
```

---

## 3. バインド関数と型

代表的な関数：

* 整数：`sqlite3_bind_int` / `sqlite3_bind_int64`
* 実数：`sqlite3_bind_double`
* 文字列：`sqlite3_bind_text` / `sqlite3_bind_text16`
* BLOB：`sqlite3_bind_blob` / `sqlite3_bind_zeroblob` / `sqlite3_bind_zeroblob64`
* NULL：`sqlite3_bind_null`

### 文字列・BLOBのライフタイム指定（重要）

第 5 引数のデストラクタ指定で **コピーの要否**を決めます。

* `SQLITE_TRANSIENT` … SQLite が **内容をコピー**（呼び出し後に元バッファを解放してよい）
* `SQLITE_STATIC` …… SQLite は **コピーしない**（メモリが *少なくとも実行完了まで* 不変であること）

文字列長に `-1` を渡すと **NUL 終端まで**を自動判定します。

---

## 4. パラメータの番号・名前を扱う補助 API

* `sqlite3_bind_parameter_count(stmt)`
  … プレースホルダ総数。
* `sqlite3_bind_parameter_name(stmt, i)`
  … i 番（1-origin）の名前（無名は `NULL`）。**`:`/`@`/`$` を含む**点に注意。
* `sqlite3_bind_parameter_index(stmt, ":name")`
  … 名前から番号へ逆引き。**文中と同じ接頭辞**（`:`など）を含める必要があります。

---

## 5. 未バインドの挙動・エラー

* **未バインド**のパラメータは **`NULL` として扱われます**（エラーにはなりません）。
  期待しない `NULL` 挙動を避けるには `sqlite3_bind_parameter_count` で個数を確認するなどの防御が有効。
* 実行中（`sqlite3_step` 中）に同じステートメントを再バインドすることはできません。
* 1 つの `sqlite3_stmt*` は **スレッドセーフではありません**。スレッド間で共有しない。

---

## 6. 再利用とパフォーマンス

* **`sqlite3_prepare_v2` を使い回し**、バインドだけ差し替えるのが最速。
  ループで `sqlite3_step` → `sqlite3_reset` → `sqlite3_bind_*` を繰り返す。
* 大量 INSERT では **トランザクション**を張る（`BEGIN`〜`COMMIT`）ことで I/O を大幅削減。
* BLOB を大きく書く場合は `sqlite3_bind_zeroblob64` ＋ **インクリメンタル BLOB I/O**（`sqlite3_blob_*`）が有効。

---

## 7. よくある落とし穴

* **識別子置換は不可**：`SELECT * FROM :table` はエラー。識別子は安全に構築・エスケープし、プリペアを作り直す。
* **IN 句の可変長**：`IN (?)` に「配列」を直接バインドすることはできません。

  * 解法例：`IN (?1,?2,?3)` を必要個数だけ生成、または一時テーブル/CTE へ投入して結合。
* **名前つきの接頭辞**：`sqlite3_bind_parameter_index(stmt, "name")` は **見つかりません**。`":name"` を渡すこと。
* **`SQLITE_STATIC` の誤用**：一時バッファに対して指定するとダングリング参照になる。迷ったら `SQLITE_TRANSIENT`。

---

## 8. 例：同名パラメータの共有

```c
sqlite3_prepare_v2(db,
  "SELECT * FROM t WHERE a >= :lo AND a < :hi OR b BETWEEN :lo AND :hi",
  -1, &stmt, NULL);

int lo = sqlite3_bind_parameter_index(stmt, ":lo");
int hi = sqlite3_bind_parameter_index(stmt, ":hi");

sqlite3_bind_int(stmt, lo, 10);
sqlite3_bind_int(stmt, hi, 20);
/* :lo は 2 箇所、:hi も 2 箇所で参照されるが、バインドは 1 回で済む */
```

---

## 9. 例：BLOB 先頭 N バイトで索引付き検索（式インデックス併用）

```sql
-- 先頭 1024 バイトの式インデックス
CREATE INDEX ix_head1k ON media_object(substr(data_bytes,1,1024));
```

```c
/* 範囲（前方一致）検索 */
sqlite3_prepare_v2(db,
  "SELECT rowid FROM media_object "
  "WHERE substr(data_bytes,1,?) >= :lo "
  "  AND substr(data_bytes,1,?) <  :hi", -1, &stmt, NULL);

sqlite3_bind_int (stmt, 1, prefix_len);
sqlite3_bind_int (stmt, 2, prefix_len);
sqlite3_bind_blob(stmt, sqlite3_bind_parameter_index(stmt, ":lo"),
                  lo_buf, prefix_len, SQLITE_TRANSIENT);
sqlite3_bind_blob(stmt, sqlite3_bind_parameter_index(stmt, ":hi"),
                  hi_buf, prefix_len, SQLITE_TRANSIENT);
```

---

## 10. Python との対応

Python の例は C API のラッパです（DB-API 2.0）。

```python
cur.execute("INSERT INTO t(a,b) VALUES(?,?)", (42, "hello"))
cur.execute("SELECT * FROM t WHERE a BETWEEN :lo AND :hi", {"lo":10, "hi":20})
```

内部では：

* `sqlite3_prepare_v2`（ステートメント作成）
* `sqlite3_bind_*`（型に応じたバインド）
* `sqlite3_step`（実行）
* `sqlite3_reset`（再利用時）

が呼ばれています。**プレースホルダの構文は C API の仕様**そのものです。

---

## 11. 参照 API 一覧（抜粋）

* 準備・実行：`sqlite3_prepare_v2` / `sqlite3_step` / `sqlite3_reset` / `sqlite3_finalize`
* パラメータ：`sqlite3_bind_*` 各種、`sqlite3_bind_parameter_count` / `sqlite3_bind_parameter_name` / `sqlite3_bind_parameter_index` / `sqlite3_clear_bindings`
* 取得：`sqlite3_column_*` 各種
* BLOB 拡張：`sqlite3_bind_zeroblob64`、`sqlite3_blob_open` / `sqlite3_blob_write`

---

## 12. 実務指針（要点）

* **常にプレースホルダを使う**（SQL インジェクション回避・パース回数削減）。
* **`prepare` を再利用**し、**バインドだけ差し替え**る。
* 文字列/BLOB は **`SQLITE_TRANSIENT` を基本**（安全側）。
* 可変長の `IN (…)` は「展開した SQL を生成」または「一時表/CTE」を使う。
* ステートメントをスレッド間で共有しない。

以上。プレースホルダの正しい理解は、**性能**（prepare 再利用）と **安全性**（SQLi防止）に直結します。

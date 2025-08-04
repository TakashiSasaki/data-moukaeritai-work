# データ公開コアスキーマのサンプル

このリポジトリは、データ生成と公開を最小限のメタデータで表現する **GenPub Core** スキーマのサンプル実装です。

## ファイル構成

### `genpub_core.py`
GenPub Core スキーマを Python の `dataclass` として定義します。`Record` クラスはデータ生成者名や公開先 URI などのメタデータを保持し、
名前に制御文字やフォーマット制御文字が含まれないよう検証を行います。また、辞書形式への変換 (`to_dict`) とその逆 (`from_dict`) を提供します。

### `store_records.py`
`genpub_core.Record` を SQLite データベースに保存するための簡単なスクリプトです。`init_db()` で `records` テーブルを作成し、
`insert_record()` でレコードを挿入します。スクリプトとして実行するとサンプルの `Record` を挿入します。

## テスト
`genpub_core.Record` の振る舞いは `pytest` でテストできます。

```bash
pip install pytest  # 未インストールの場合
pytest
```

上記コマンドで `tests/test_genpub_core.py` に含まれる単体テストが実行されます。

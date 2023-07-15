# NotifyLineOfAWSBilling

## 概要

特定のLINEアカウントまたはLINEグループに対して、メッセージ形式でAWS利用料金を通知します。

## 構成図

![diagram](./image/diagram.drawio.png)

## SAMデプロイ方法

1. 事前に以下の内容でParameter Storeに、LINEアクセストークンを保存

|名前|種類|値|
|---|---|---|
|/notify-aws-billing/line-access-token|SecureString|<LINEアクセストークン>|

2. 以下コマンドで、SAMアプリをビルド

``` bash
sam build
```

3. 以下コマンドで、SAMアプリをデプロイ

``` bash
sam deploy --parameter-overrides \
  DefaultKmsId=`aws kms describe-key --key-id alias/aws/ssm --query 'KeyMetadata.KeyId' --output text` \
  LineAccessToken=/notify-aws-billing/line-access-token
```

※`confirm_changeset`を有効化すると、途中で変更セットをデプロイするか確認されるので、内容問題なければ`y`を入力し続行

## 参考文献

* [AWSサービス毎の請求額を毎日LINEに通知してみた \| DevelopersIO](https://dev.classmethod.jp/articles/notify-line-aws-billing/)

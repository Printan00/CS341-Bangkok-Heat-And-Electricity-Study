# คู่มือรัน BHES

รันคำสั่งจากราก repo เว้นแต่ขั้นตอนจะระบุให้เข้าโฟลเดอร์ `frontend/` ถ้าต้องการเปิดแดชบอร์ดโดยใช้ API ของทีมที่มีอยู่แล้ว เริ่มที่ [เชื่อมแดชบอร์ดกับ AWS](#เชื่อมแดชบอร์ดกับ-aws)

## เตรียมเครื่องและข้อมูล

ใช้ AWS CLI v2 กับโปรไฟล์หรือ IAM role ที่ทีมกำหนด, Terraform 1.10 ขึ้นไป และ Python ที่ติดตั้ง `pyarrow` ได้ สำหรับ Python ใช้ 3.13 ให้ตรงกับ Lambda runtime ได้ ส่วน Next.js ต้องใช้ Node.js 20.9 ขึ้นไป

```bash
export AWS_DEFAULT_REGION=ap-southeast-1
aws sts get-caller-identity

python3.13 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
```

`scripts/ingest.py` ค้นหาชื่อไฟล์สำรวจทั้งสองชุดใต้ `data/` ขอไฟล์จากผู้สอนและเก็บไว้ในเครื่อง โฟลเดอร์นี้อยู่ใน `.gitignore`

จำกัดสิทธิ์เข้าถึง S3 Raw และ Quarantine เพราะแถวในสองส่วนนี้อาจมีพิกัด เก็บข้อมูลดิบ พิกัด รหัสครัวเรือน credentials และ Terraform state ไว้นอก Git

```text
data/
├── ThaiCI_Household_Questionaire/
│   └── ThaiCI_Household_Questionaire_anonymized.xlsx
└── SOVI_Survey_Questionaire/
    └── SOVI_Survey_Questionaire_anonymized.xlsx
```

ตรวจ codebook ในเครื่องได้ด้วยคำสั่งด้านล่าง ผลที่เขียนลง `reports/` เป็นค่ารวมระดับชุดข้อมูล

```bash
.venv/bin/python scripts/profile_codebook.py --data-dir data --out reports
```

## Deploy ทรัพยากร AWS

Terraform อยู่ที่ [`infra/terraform/`](../infra/terraform/) โครงการใช้ Region `ap-southeast-1` และทรัพยากรชื่อขึ้นต้นด้วย `bhes` ใช้ IAM profile หรือ role ที่มีสิทธิ์สำหรับสภาพแวดล้อมนั้น และตรวจบัญชีที่ได้จาก `aws sts get-caller-identity` ก่อนเปลี่ยนทรัพยากร

### Terraform state

ทีมที่ใช้ backend เดิมให้ใช้ค่าจาก [`versions.tf`](../infra/terraform/versions.tf) ถ้าใช้บัญชีแยก ต้องสร้าง state bucket ของบัญชีนั้นก่อนและระบุ bucket ให้ Terraform ผ่าน `-backend-config` เปิด versioning และปิด public access ของ bucket นี้ด้วย

```bash
BHES_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BHES_STATE_BUCKET="bhes-tfstate-${BHES_ACCOUNT_ID}"

aws s3api create-bucket --bucket "$BHES_STATE_BUCKET" \
  --region "$AWS_DEFAULT_REGION" \
  --create-bucket-configuration "LocationConstraint=$AWS_DEFAULT_REGION"
aws s3api put-bucket-versioning --bucket "$BHES_STATE_BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket "$BHES_STATE_BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

เริ่ม Terraform สำหรับบัญชีทีม

```bash
terraform -chdir=infra/terraform init
```

สำหรับ checkout ที่ตั้งใจใช้ state ของบัญชีแยก

```bash
terraform -chdir=infra/terraform init -reconfigure -backend-config="bucket=$BHES_STATE_BUCKET"
```

### สร้างหรืออัปเดตทรัพยากร

```bash
terraform -chdir=infra/terraform plan
terraform -chdir=infra/terraform apply
```

อ่าน plan และยืนยันเฉพาะรายการที่ตั้งใจเปลี่ยน Terraform จัดการ data lake, bucket ผล Athena, IAM, CloudWatch Logs, Lambda, Step Functions, Glue, Athena และ API Gateway ส่วน state bucket สร้างแยกไว้เก็บ state หากเปลี่ยน Region ให้ตรวจ `pandas_layer_arn` ใน [`variables.tf`](../infra/terraform/variables.tf) ด้วย

## นำเข้าและประมวลผล

ถ้าต้องการ LST ให้สร้าง CSV ระดับชุมชนและครัวเรือนก่อน ingest เตรียมสิทธิ์ Earth Engine ตาม [คู่มือ LST](../reports/gee_lst_pipeline.md) ทั้งสองไฟล์จะอยู่ใต้ `data/` และถูกข้ามถ้ายังไม่ได้สร้าง

```bash
.venv/bin/python -m pip install -r scripts/requirements-gee.txt
.venv/bin/earthengine authenticate
.venv/bin/python scripts/gee_lst.py --project '<earth-engine-project>'
```

อัปโหลดข้อมูลและเก็บ `batch_id` ที่สคริปต์พิมพ์ออกมา ไฟล์เดิมมีรหัส batch เดิม

```bash
BHES_LAKE_BUCKET=$(terraform -chdir=infra/terraform output -raw lake_bucket)
.venv/bin/python scripts/ingest.py --bucket "$BHES_LAKE_BUCKET"
```

ใส่ batch ID จริงแล้วเริ่ม Step Functions

```bash
BHES_STATE_MACHINE=$(terraform -chdir=infra/terraform output -raw state_machine_arn)
BHES_BATCH_ID='<batch-id-from-ingest>'
BHES_EXECUTION=$(aws stepfunctions start-execution \
  --state-machine-arn "$BHES_STATE_MACHINE" \
  --input "{\"batch_id\":\"$BHES_BATCH_ID\"}" \
  --query executionArn --output text)

aws stepfunctions describe-execution --execution-arn "$BHES_EXECUTION" \
  --query status --output text
```

- ถ้ามี `gee_lst` และ `gee_lst_household` ให้รันสอง batch นี้ก่อน Happy Home เพื่อให้ Integrate อ่าน `community_dim` และ `household_lst` ที่เผยแพร่แล้ว
- Batch เดิมที่มี `_SUCCESS.json` จะไปที่ `SkipDuplicate` หากอัปเดตกฎหรือเพิ่ม LST แล้วต้องประมวลผล Happy Home เดิมใหม่ ให้ส่ง `{"batch_id":"<batch-id>","force":true}`
- SoVI ถูกนำเข้า Raw เพื่อเก็บต้นฉบับและเทียบข้อมูลระดับกลุ่ม หากส่ง batch SoVI เข้า workflow จะหยุดที่ `ValidationFailed` เพราะยังไม่มีกฎ Validate สำหรับชุดนี้
- เมื่อ Validate ไม่ผ่าน ให้เริ่มตรวจที่ `quarantine/<source>/<batch_id>/dq_report.json` ส่วนกรณี Lambda หรือ Step Functions ล้ม ให้ดูประวัติ execution และ CloudWatch Logs

## ลงทะเบียนตารางและรัน Athena

เริ่ม Glue crawler หลัง Verify เผยแพร่ Parquet แล้ว โดยเฉพาะเมื่อเพิ่มตารางหรือคอลัมน์ เช่น `income_group`, `burden_class` และ `has_aircon` ใน `happy_home_risk`

```bash
BHES_CRAWLER=$(terraform -chdir=infra/terraform output -raw glue_crawler)
aws glue start-crawler --name "$BHES_CRAWLER"
aws glue get-crawler --name "$BHES_CRAWLER" \
  --query '{State:Crawler.State,LastStatus:Crawler.LastCrawl.Status}'
```

รอให้ crawler กลับเป็น `READY` และรอบล่าสุดเป็น `SUCCEEDED` แล้วลอง query สรุป Q2 จาก SQL ชุดเดียวกับแดชบอร์ด

```bash
BHES_QUERY_ID=$(aws athena start-query-execution --work-group bhes-wg \
  --query-execution-context Database=bhes \
  --query-string file://services/dashboard_query/q2.sql \
  --query QueryExecutionId --output text)

aws athena get-query-execution --query-execution-id "$BHES_QUERY_ID" \
  --query QueryExecution.Status.State --output text
# รอให้สถานะเป็น SUCCEEDED ก่อนอ่านผล
aws athena get-query-results --query-execution-id "$BHES_QUERY_ID"
```

ชุด SQL วิจัยใน `analytics/` แยกจาก query สำหรับแดชบอร์ด รันซ้ำและสร้าง CSV ได้ด้วยคำสั่งต่อไปนี้ การรันคำสั่งแรกจะเขียนผลลง `analytics/results/` ส่วนคำสั่งเทียบผลต้องมีไฟล์ Happy Home ใน `data/`

```bash
.venv/bin/python analytics/run_athena.py
.venv/bin/python analytics/compare_athena_local.py --data-dir data
.venv/bin/python analytics/significance.py --write
.venv/bin/python dashboard/build.py
```

## เชื่อมแดชบอร์ดกับ AWS

ติดตั้ง dependency และสร้างไฟล์ตั้งค่า

```bash
cd frontend
npm ci
test -f .env.local || cp .env.example .env.local
```

ผู้ที่เข้าถึง Terraform state ได้สามารถดู URL ด้วย `terraform -chdir=../infra/terraform output -raw dashboard_q3_api_url` จากโฟลเดอร์ `frontend/` หรือขอ URL จากคนดูแล AWS ของทีม

| ตัวแปรฝั่งเซิร์ฟเวอร์ | ค่า |
| --- | --- |
| `Q3_API_URL` | URL HTTPS ของ API Gateway ที่ลงท้ายด้วย `/dashboard/q3` |
| `Q1_API_URL`, `Q2_API_URL` | ตั้งเมื่อใช้ Gateway คนละตัวกับ Q3 หรือเมื่อต้องการระบุ URL โดยตรง |
| `AWS_PROFILE` | ชื่อโปรไฟล์ AWS บนเครื่อง เช่น `default` ซึ่งมีสิทธิ์ `execute-api:Invoke` สำหรับเส้นทางที่ใช้ |

Terraform output `dashboard_q1_invoke_arn`, `dashboard_q2_invoke_arn` และ `dashboard_q3_invoke_arn` ใช้ประกอบการกำหนดสิทธิ์อ่านผลสรุป ส่วน `dashboard_q2_households_invoke_arn` และ `dashboard_q3_households_invoke_arn` เป็นสิทธิ์แยกสำหรับตารางรายครัวเรือนใน local dev ให้เฉพาะผู้ที่ได้รับอนุญาตตรวจข้อมูลรายแถว

```bash
npm run dev
```

เปิด **http://localhost:3000** โหมด dev bind กับ loopback และตารางรายครัวเรือนแสดงเฉพาะ Q2/Q3 บน dev ในเครื่อง สำหรับ production ใช้สิทธิ์อ่านเส้นทางผลสรุปและเก็บ credentials ฝั่งเซิร์ฟเวอร์ ไฟล์ `.env.local` ถูกกันจาก Git แล้ว

### Deploy Next.js frontend บน Vercel

สร้าง Vercel project จาก repository แล้วกำหนด **Root Directory** เป็น `frontend` โดยใช้ Next.js preset และ build command `npm run build` ตั้ง Production Branch เป็น `main` โค้ดจะเรียก API Gateway ด้วย AWS SigV4 จากฝั่ง server; ห้ามอัปโหลด `.env.local`, AWS access key หรือ `AWS_PROFILE` ไป Vercel

ดูรายละเอียด OIDC issuer และ trust policy ล่าสุดจาก [Vercel: Connect to AWS](https://vercel.com/docs/oidc/aws)

ใช้ Vercel OIDC เพื่อให้ function รับ AWS credentials ชั่วคราว:

1. ใน AWS IAM เพิ่ม OpenID Connect provider ของ Vercel โดยใช้ issuer `https://oidc.vercel.com/<team-slug>` และ audience `https://vercel.com/<team-slug>` ตาม team slug ของ Vercel
2. สร้าง IAM role ที่ trust เฉพาะ Vercel project และ production environment นั้น ตัวอย่างเงื่อนไขใน trust policy:

   ```json
   {
     "StringEquals": {
       "oidc.vercel.com/<team-slug>:aud": "https://vercel.com/<team-slug>",
       "oidc.vercel.com/<team-slug>:sub": "owner:<team-slug>:project:<project-name>:environment:production"
     }
   }
   ```

   ให้กำหนด Federated principal เป็น `arn:aws:iam::<account-id>:oidc-provider/oidc.vercel.com/<team-slug>` และ action เป็น `sts:AssumeRoleWithWebIdentity` อย่าใช้ wildcard สำหรับ project หรือ environment โดยไม่จำเป็น
3. แนบ permission policy ให้ role นี้เรียกได้เฉพาะเส้นทางสรุป `execute-api:Invoke` โดยใช้ ARN จาก Terraform outputs `dashboard_q1_invoke_arn`, `dashboard_q2_invoke_arn` และ `dashboard_q3_invoke_arn` เท่านั้น ไม่ต้องให้สิทธิ์ `dashboard_q2_households_invoke_arn` หรือ `dashboard_q3_households_invoke_arn`
4. เพิ่ม Environment Variables ใน Vercel project (Production): `AWS_ROLE_ARN` เป็น ARN ของ role, `Q3_API_URL` เป็น URL จาก `dashboard_q3_api_url` และตั้ง `Q1_API_URL`/`Q2_API_URL` เมื่อใช้ API Gateway คนละตัวกับ Q3 หากต้องการ Preview deployment ให้เพิ่ม trust สำหรับ preview แยกต่างหากและจำกัด project/environment เช่นเดียวกัน

หน้าเว็บจะแสดงผลสรุปจาก AWS โดยไม่เก็บ long-lived AWS keys บน Vercel ส่วนตารางรายครัวเรือนยังปิดใน Vercel ตาม `canViewHouseholdDetails()` และการตั้งค่า Vercel ควรทำโดยผู้ดูแล AWS/Vercel ของทีม

## ทดสอบและแก้ปัญหา

จากราก repo รันชุดเทสต์ Python ด้วยข้อมูลสังเคราะห์ได้โดยไม่ต้องเชื่อม AWS

```bash
.venv/bin/python -m pip install -r tests/requirements.txt
.venv/bin/python -m pytest tests
```

เพิ่มเทสต์กับไฟล์จริงได้เมื่อมีสิทธิ์ใช้ข้อมูลและวางไฟล์ไว้ถูกที่

```bash
BHES_SAMPLE_DIR=data/ThaiCI_Household_Questionaire .venv/bin/python -m pytest tests
```

เทสต์กับไฟล์จริงจะข้ามเมื่อไม่พบไฟล์ตามที่กำหนด ชุดเทสต์ pipeline ใช้ S3 จำลองและตรวจด้วยว่า Verify ที่ไม่ผ่านจะไม่เผยแพร่ผล

ตรวจ frontend จาก `frontend/`

```bash
npm run lint
npm run typecheck
npm run build
```

| อาการ | จุดตรวจ |
| --- | --- |
| Terraform เข้า backend ไม่ได้ | ตรวจ AWS profile, บัญชี, state bucket และสิทธิ์อ่านหรือเขียน state ของสภาพแวดล้อมนั้น |
| Ingest หาไฟล์ไม่พบ | ตรวจชื่อไฟล์และโฟลเดอร์ `data/` ให้ตรงกับ [ชื่อที่สคริปต์ค้นหา](../scripts/ingest.py) |
| Step Functions ไปที่ `SkipDuplicate` | ตรวจ `batch_id` ถ้าต้องคำนวณซ้ำหลังอัปเดตกฎให้ส่ง `force: true` |
| Athena แจ้ง `TABLE_NOT_FOUND` หรือ `COLUMN_NOT_FOUND` | ตรวจว่า Verify เผยแพร่ Parquet แล้วและ Glue crawler รอบล่าสุดสำเร็จหลังแก้ schema |
| หน้าเว็บแจ้งว่าโหลดข้อมูลไม่ได้ | ตรวจ API URL, profile และสิทธิ์ `execute-api:Invoke` ที่ ARN ของเส้นทางนั้น คำขอที่ไม่มีลายเซ็น SigV4 จะถูกปฏิเสธ |
| `pip` ติดตั้ง `pyarrow` ไม่สำเร็จ | สร้าง virtual environment ใหม่ด้วย Python 3.13 แล้วติดตั้งจาก `tests/requirements.txt` |

### ผลตรวจที่ทีมบันทึกไว้

- รอบทดสอบบน AWS วันที่ 12 พ.ย. 2026 ใช้ Happy Home 88 แถว ผ่าน Validate และ Verify ครบ รันไฟล์เดิมซ้ำไปที่ `SkipDuplicate` และรันด้วย `force` สำเร็จ ส่วน SoVI หยุดที่ `ValidationFailed` ตามที่ออกแบบไว้
- ชุดผลวิจัยใน `analytics/` ตรวจเทียบกับการคำนวณแยกจากไฟล์ดิบแล้ว **198 เซลล์ตรงกันทั้งหมด** ดู [บันทึกผลตรวจ](../analytics/results/verification.json) และ [วิธีตรวจ](../reports/q1_q3_findings.md)
- ตัวอย่างผลสำหรับแดชบอร์ดอยู่ใน [Athena exports Q1–Q3](../reports/athena-exports/) และบันทึกการทดสอบ LST อยู่ใน [รายงาน Earth Engine](../reports/gee_lst_pipeline.md)

### เมื่อเลิกใช้สภาพแวดล้อมทดลอง

ให้ผู้ดูแลบัญชีตรวจว่าจะเก็บข้อมูลและผล Athena ส่วนไหนก่อนลบทรัพยากร Terraform จะลบ bucket ที่ยังมีข้อมูลไม่ได้ และ data lake ที่เปิด versioning ต้องจัดการทั้ง object versions กับ delete markers หลังตรวจบัญชีและ plan ของสภาพแวดล้อมทดลองแล้วจึงใช้ `terraform destroy` ส่วน state bucket สร้างแยกและให้ผู้ดูแลจัดการตามนโยบายเก็บข้อมูลของทีม

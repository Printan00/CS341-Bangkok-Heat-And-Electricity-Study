# CS341 Bangkok Heat & Electricity Study (BHES)

โครงงานระบบวิศวกรรมข้อมูล (Data Pipeline บน AWS) เพื่อศึกษา **ความเปราะบางต่อความร้อน** และ **ภาระค่าไฟฟ้า** ของครัวเรือนรายได้น้อยในกรุงเทพมหานคร
รวบรวม ตรวจคุณภาพ จัดเก็บ และวิเคราะห์ข้อมูลสำรวจจริง โดยไม่สรุปเชิงเหตุและผลเกินกว่าหลักฐานที่มี

## สารบัญ
1. [ภาพรวม คำถามวิจัย และข้อมูล](#1-ภาพรวม-คำถามวิจัย-และข้อมูล)
2. [สถาปัตยกรรม](#2-สถาปัตยกรรม)
3. [ผลวิเคราะห์โดยสรุป (Q1–Q3)](#3-ผลวิเคราะห์โดยสรุป-q1q3)
4. [วิธีรัน (Quick start)](#4-วิธีรัน-quick-start)
5. [รายละเอียดการทำงานของ pipeline](#5-รายละเอียดการทำงานของ-pipeline)
6. [ทรัพยากร AWS และสิทธิ์](#6-ทรัพยากร-aws-และสิทธิ์)
7. [โครงสร้าง repo](#7-โครงสร้าง-repo)
8. [ข้อค้นพบจากการตรวจข้อมูล](#8-ข้อค้นพบจากการตรวจข้อมูล)
9. [สถานะงาน](#9-สถานะงาน)
10. [สมาชิกทีม](#10-สมาชิกทีม)
11. [บันทึกการใช้ AI](#11-บันทึกการใช้-ai)
12. [ข้อตกลงของทีม](#12-ข้อตกลงของทีม)

---

## 1. ภาพรวม คำถามวิจัย และข้อมูล

ครัวเรือนในเมืองได้รับผลกระทบจากความร้อนไม่เท่ากัน ขึ้นกับลักษณะบ้าน (วัสดุหลังคา การระบายอากาศ) ร่มเงารอบบ้าน รายได้และความสามารถในการปรับตัว การเข้าถึงอุปกรณ์ทำความเย็น และค่าใช้จ่ายด้านพลังงาน

| ข้อ | คำถามวิจัย |
|---|---|
| **Q1** Urban Heat Vulnerability | ลักษณะบ้าน เช่น วัสดุหลังคา ร่มเงา และการระบายอากาศ สัมพันธ์กับผลกระทบจากความร้อนอย่างไร และครัวเรือนกลุ่มใดมีข้อจำกัดในการรับมือมากที่สุด |
| **Q2** Heat & Energy Burden | ภาระค่าไฟเมื่อเทียบกับรายได้แตกต่างกันอย่างไรระหว่างกลุ่มรายได้ และระหว่างครัวเรือนที่เข้าถึงการทำความเย็นต่างกัน |
| **Q3** Household Support Prioritization | เมื่อพิจารณาผลกระทบจากความร้อน ภาระค่าไฟ และข้อจำกัดในการปรับปรุงบ้าน ครัวเรือนกลุ่มใดควรได้รับการสนับสนุนก่อน และปัจจัยใดทำให้บางครัวเรือนปรับปรุงบ้านได้ ขณะที่บางครัวเรือนทำไม่ได้ |

### แหล่งข้อมูล

| ข้อมูล | ปีที่สำรวจ | ขนาด | ใช้ทำอะไร |
|---|---|---|---|
| **Happy Home / ThaiCI** (Nature-based Solutions Survey) | 2026 (สัมภาษณ์ ก.ค. 2026) | 88 ครัวเรือน จาก 2 ชุมชนริมคลองเปรมประชากร เขตหลักสี่ | **ข้อมูลหลักของ Q1–Q3** มีลักษณะบ้าน ผลกระทบความร้อน ค่าไฟ เครื่องใช้ไฟฟ้า |
| **SoVI V8** (Social Vulnerability Survey) | 2023 | 500 ครัวเรือน จาก 17 ชุมชนในกรุงเทพฯ และปริมณฑล | บริบทระดับกลุ่มของ Q3 เท่านั้น (ไม่มีค่าไฟและตัวแปรความร้อน) |
| Landsat / Earth Engine (ทางเลือก) | – | ระดับชุมชน | ตัวแปรเสริมของ Happy Home (`scripts/gee_lst.py` ยังไม่ได้รันจริง) |

> **ข้อมูลสำรวจดิบไม่อยู่ใน repo** (repo เป็น public และข้อมูลไม่ผ่าน k-anonymity) เก็บเฉพาะในโฟลเดอร์ `data/` ในเครื่อง ซึ่งอยู่ใน `.gitignore` ขอไฟล์ได้จากผู้สอนวิชา
> ทั้งสองชุด **ไม่ join รายครัวเรือน** (ต่างปี ต่างพื้นที่ ต่างชั้นรายได้) เทียบได้เฉพาะระดับกลุ่ม ดู [reports/integration_feasibility.md](reports/integration_feasibility.md)

---

## 2. สถาปัตยกรรม

ไฟล์ต้นฉบับแก้ใน draw.io ได้: [architecture/bhes_architecture_v2.drawio.svg](architecture/bhes_architecture_v2.drawio.svg) (วิธีอัปเดตภาพดู [architecture/README.md](architecture/README.md))

[![BHES Data Architecture](architecture/bhes_architecture_v2.png)](architecture/bhes_architecture_v2.png)

**เส้นทางของข้อมูล:** แบบสำรวจ (xlsx) → **Ingest** → **Raw** → **Validate** (ไม่ผ่าน → **Quarantine**) → **Transform** → **Trusted** → **Integrate** → **Curated** → **Verify** → **Glue Data Catalog + Athena** → รายงานผล (QuickSight เป็นทางเลือก)

| ส่วน | บริการ | หน้าที่ |
|---|---|---|
| Ingest | AWS CLI + Python | อัปโหลดไฟล์เข้า S3 พร้อม batch_id, source, วันที่ ไม่เขียนทับต้นฉบับ |
| Orchestration | Step Functions + Lambda | CheckBatch → Validate → Transform → Integrate → Verify ต่อ batch |
| Raw (S3) | Amazon S3 | เก็บไฟล์ต้นฉบับทุกครั้งที่มาถึง จำกัดสิทธิ์ (arrival ≠ acceptance) |
| Quarantine (S3) | Amazon S3 | แถวที่ไม่ผ่าน Validate พร้อมรายงานเหตุผล ไม่ลบทิ้ง |
| Trusted (S3, Parquet) | Amazon S3 | ข้อมูลที่ผ่านการตรวจ รหัสครัวเรือนนามแฝง ตัดพิกัด/ชื่อออก |
| Curated (S3, Parquet) | Amazon S3 | ตารางวิเคราะห์ตอบ Q1–Q3 พร้อม lineage (batch_id, source) |
| Query layer | Glue (Crawler + Data Catalog) + Athena | สร้างตารางจาก Parquet แล้ว query ด้วย SQL จ่ายตามข้อมูลที่สแกน |
| Dashboard (ทางเลือก) | QuickSight | ใช้ Athena เป็นแหล่งข้อมูล เห็นเฉพาะตารางสรุปกลุ่ม n ≥ 5 |
| Security & operations | IAM, CloudWatch | สิทธิ์น้อยที่สุด, run log และรายงานตรวจคุณภาพ |
| IaC | Terraform | สร้างทรัพยากรทั้งหมดให้รันซ้ำได้ |

### หลักการออกแบบ
- **Validate ก่อน Transform:** ข้อมูลที่ยังไม่ผ่านการตรวจจะไม่ถูกแปลง
- **รันซ้ำได้:** CheckBatch ดู `_SUCCESS.json` ถ้า batch นี้ประมวลผลแล้วจะหยุด ไม่เกิดข้อมูลซ้ำ
- **รันสำเร็จ ≠ ข้อมูลถูกต้อง:** ขั้น Verify ตรวจจำนวนแถว ฟิลด์บังคับ schema และยอดรวมก่อนเขียน `_SUCCESS.json`
- **ความเป็นส่วนตัว:** ไม่มีข้อมูลดิบบน GitHub ไม่มีพิกัดใน Trusted/Curated และรายงานซ่อนเซลล์ n < 5
- **ไม่ join สองชุดสำรวจรายครัวเรือน** เทียบระดับกลุ่มเท่านั้น

---

## 3. ผลวิเคราะห์โดยสรุป (Q1–Q3)

ใช้ Happy Home ชุดเดียว (88 ครัวเรือน) ผ่าน Athena รายละเอียด ตัวเลข และข้อจำกัดอยู่ใน [reports/q1_q3_findings.md](reports/q1_q3_findings.md)
SQL อยู่ใน [analytics/](analytics/) ผล CSV (ซ่อน n < 5 แล้ว) อยู่ใน [analytics/results/](analytics/results/)

| ข้อ | ผล | สาระ |
|---|---|---|
| Q1 | **ยังไม่เพียงพอ** | ผนังไม้สัมพันธ์กับผลกระทบความร้อนสูง 45.9% เทียบ 21.6% (p = 0.021) ระบายอากาศไม่ดีไปทางเดียวกันแต่ยังไม่มีนัย หลังคา ฝ้า ร่มเงาไม่เป็นไปตามที่คาด ฉนวนทดสอบไม่ได้ (81/88 ไม่มี) |
| Q2 | **สนับสนุน** | รายได้ไม่เกิน 10,000 บาท/เดือน มีภาระค่าไฟสูง (≥ 10%) 79.4% เทียบ 14.8% (p < 0.001) การมี/ไม่มีแอร์ไม่ต่างกัน (39.1% เทียบ 40.5%) |
| Q3 | **สนับสนุน** (กลุ่มที่ควรช่วยก่อน) / **ยังไม่เพียงพอ** (ปัจจัยปรับปรุงบ้าน) | 21 บ้านลำดับต้นคือรายได้ต่ำ + ภาระค่าไฟสูง ลำดับเหมือนกันทั้งน้ำหนักค่าไฟ ×2 และน้ำหนักเท่ากัน เคยปรับปรุงบ้านเพียง 11 หลัง |

ผลทั้งหมดเป็นความสัมพันธ์ ไม่ใช่เหตุและผล (n = 88 จาก 2 ชุมชน คำตอบรายงานเองย้อนหลัง ทดสอบหลายครั้งโดยไม่ปรับค่า p)
ผล Athena ตรวจซ้ำกับการคำนวณจากไฟล์ดิบด้วยโค้ดแยกจาก pipeline (`analytics/recheck_local.py`): เทียบ 198 เซลล์ที่แสดงอยู่ ต่างกัน 0

**Dashboard (ไทย/อังกฤษ, 1 หน้าต่อคำถาม + heatmap 2 อัน):** เปิด [`dashboard/index.html`](dashboard/index.html) ในเบราว์เซอร์ได้เลย (ไฟล์เดียว ไม่ต้องติดตั้ง ต้องมีอินเทอร์เน็ตเพื่อโหลดฟอนต์) สร้างจากไฟล์ CSV ผล Athena ด้วย `python dashboard/build.py` ตัวเลขทุกตัวอ่านจาก CSV ไม่พิมพ์เอง แต่ละกราฟมีปุ่ม “ดู SQL” และ build จะหยุดถ้าพบจำนวน 1–4 บ้านในคอลัมน์จำนวน

---

## 4. วิธีรัน (Quick start)

### 4.1 สิ่งที่ต้องมี

| เครื่องมือ | เวอร์ชัน | หมายเหตุ |
|---|---|---|
| บัญชี AWS | – | ใช้ **IAM user/role** ไม่ใช้ root access key ในงานประจำ Region `ap-southeast-1` (Singapore) |
| AWS CLI | v2 | ตั้งค่า credentials ด้วย `aws configure` หรือ SSO ทดสอบด้วย `aws sts get-caller-identity` |
| Terraform | ≥ 1.10 | (ต้องมี `use_lockfile` ของ S3 backend) |
| Python | 3.11–3.14 | ทีมทดสอบกับ 3.11 และ 3.14 ส่วน 3.15 ติดตั้ง pyarrow ค้างในการทดลองของเรา ให้ใช้เวอร์ชันที่ต่ำกว่า |
| ข้อมูลสำรวจ 2 ไฟล์ | – | ขอจากผู้สอน ดู 4.2 |

ค่าใช้จ่ายต่ำมากกับข้อมูลขนาดนี้ (Athena สแกนน้อยกว่า 4 KB ต่อคำสั่ง) แต่ Glue Crawler, Step Functions, Lambda และ S3 มีค่าใช้จ่าย ควรตั้ง **AWS Budget alert** ก่อนเริ่ม และ `terraform destroy` เมื่อเลิกใช้ (4.9)

```bash
git clone https://github.com/Printan00/CS341-Bangkok-Heat-And-Electricity-Study.git
cd CS341-Bangkok-Heat-And-Electricity-Study
export AWS_DEFAULT_REGION=ap-southeast-1
aws sts get-caller-identity          # ต้องได้ Account ID ของคุณ (จดไว้: <ACCOUNT_ID>)
```

### 4.2 วางข้อมูลที่ `data/`
สร้างโฟลเดอร์ `data/` ที่ราก repo แล้ววางไฟล์ตามชื่อและโครงนี้เป๊ะ (สคริปต์ค้นหาตามชื่อไฟล์นี้)

```
data/
├── ThaiCI_Household_Questionaire/
│   ├── ThaiCI_Household_Questionaire_anonymized.xlsx     (Happy Home)
│   └── ThaiCI_Household_Questionaire.docx                (แบบสอบถาม ไม่บังคับ)
└── SOVI_Survey_Questionaire/
    ├── SOVI_Survey_Questionaire_anonymized.xlsx          (SoVI)
    └── SOVI_Survey_Questionaire.docx                     (แบบสอบถาม ไม่บังคับ)
```

`data/` อยู่ใน `.gitignore` ห้าม commit ถ้าไม่มีไฟล์จริง ยังรัน **เทสต์** (4.8) ได้ด้วยข้อมูลสังเคราะห์ แต่ ingest และรัน pipeline ไม่ได้

### 4.3 ตรวจ codebook (ไม่ใช้ AWS)
```bash
python -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/profile_codebook.py --data-dir data --out reports
```
ได้ค่ารวมเท่านั้น (เซลล์ n < 5 เป็น `<5` ไม่มีพิกัดหรือรหัสครัวเรือน) ผลอยู่ใน `reports/`

### 4.4 สร้าง bucket เก็บ Terraform state (ครั้งแรกต่อบัญชี AWS)
state bucket สร้างด้วยมือ ไม่อยู่ใน Terraform เพื่อไม่ให้ `destroy` ลบ state ของตัวเอง

```bash
B=bhes-tfstate-<ACCOUNT_ID>; R=ap-southeast-1
aws s3api create-bucket --bucket $B --region $R --create-bucket-configuration LocationConstraint=$R
aws s3api put-bucket-versioning --bucket $B --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket $B --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

**ถ้าใช้บัญชี AWS ของตัวเอง (ไม่ใช่ของทีม)** ต้องแก้ชื่อ bucket ในบล็อก `backend "s3"` ของ `infra/terraform/versions.tf` ให้เป็น `bhes-tfstate-<ACCOUNT_ID>` ของคุณ มิฉะนั้น `terraform init` จะชี้ไปที่ state ของทีม

### 4.5 Deploy ทรัพยากรด้วย Terraform
```bash
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform plan      # ดูก่อนเสมอ ครั้งแรกจะสร้างทรัพยากรใหม่ทั้งหมด
terraform -chdir=infra/terraform apply     # ตอบ yes เมื่อตรวจ plan แล้ว
```
สร้าง: S3 (data lake, ผล Athena), IAM, Lambda 5 ตัว, Step Functions `bhes-pipeline`, Glue database/crawler, Athena workgroup `bhes-wg` (รายการเต็มในข้อ 6) และ Lambda layer ที่ให้ pyarrow เป็นของ AWS ใน Region เดียวกัน (ตัวแปร `pandas_layer_arn`) หลัง apply รัน `plan` ซ้ำ ต้องได้ "No changes"

### 4.6 Ingest ข้อมูลเข้า Raw
```bash
.venv/bin/pip install -r scripts/requirements.txt          # openpyxl, boto3
.venv/bin/python scripts/ingest.py --bucket $(terraform -chdir=infra/terraform output -raw lake_bucket)
```
สคริปต์พิมพ์ `batch_id` ของแต่ละไฟล์ (เช่น `happy_home-26cba344f87c`, `sovi-7fb4858da401`) **จดไว้ใช้ต่อ** ไฟล์ขึ้น `incoming/` แล้ว copy เข้า `raw/<source>/<batch_id>/` พร้อม metadata และ `_manifest.json` จากนั้นลบจาก `incoming/`
`batch_id = <source>-<sha256 12 ตัวแรก>` ไฟล์เนื้อหาเดิมได้ `batch_id` เดิม รันซ้ำจะขึ้น SKIP ไม่เขียนทับ

### 4.7 รัน pipeline → Glue → Athena
```bash
SM=$(terraform -chdir=infra/terraform output -raw state_machine_arn)
BATCH=happy_home-26cba344f87c            # ใช้ batch_id ที่ ingest พิมพ์ออกมา

EX=$(aws stepfunctions start-execution --state-machine-arn $SM \
      --input "{\"batch_id\":\"$BATCH\"}" --query executionArn --output text)
aws stepfunctions describe-execution --execution-arn $EX --query status --output text   # รอจน SUCCEEDED
```
สถานะที่คาดหวัง: Happy Home → `SUCCEEDED` (ผ่าน 88 ถูกแยก 0), SoVI → `FAILED` ที่ `ValidationFailed` (ยังไม่มีกฎของ SoVI ตั้งใจให้หยุด) ดูเหตุผลที่ `quarantine/<source>/<batch_id>/dq_report.json`

จากนั้น crawl ตารางแล้ว query:
```bash
aws glue start-crawler --name bhes-curated
aws glue get-crawler --name bhes-curated --query Crawler.State --output text           # รอจน READY
aws athena start-query-execution --work-group bhes-wg --query-execution-context Database=bhes \
     --query-string 'SELECT count(*) FROM happy_home_household'                          # ควรได้ 88
```

รันชุด SQL ของ Q1–Q3 ทั้งหมด (30 คำสั่ง) และเก็บเป็น CSV ต่อคำสั่ง:
```bash
python analytics/run_athena.py                  # → analytics/results/{q1,q2,q3,data_quality}/Qx_y.csv
python analytics/compare_athena_local.py --data-dir data   # เทียบกับการคำนวณใหม่จากไฟล์ดิบ (ต้องได้ 0 mismatches)
python analytics/significance.py --write        # ค่า p (Fisher exact) จากเซลล์ที่แสดงอยู่
```
(สองสคริปต์หลังต้องมี `openpyxl`; ถ้าใช้ `.venv` ข้างบนก็มีอยู่แล้ว)

### 4.8 เทสต์อัตโนมัติ
```bash
python -m venv .venv-test && .venv-test/bin/pip install -r tests/requirements.txt
.venv-test/bin/python -m pytest tests                                    # ข้อมูลสังเคราะห์ ไม่ต้องมีไฟล์จริง
BHES_SAMPLE_DIR=data/ThaiCI_Household_Questionaire .venv-test/bin/python -m pytest tests   # เพิ่มเทสต์กับไฟล์จริง (ตรวจตัวเลขในสเปก D1–D7)
```
ผลล่าสุด (12 พ.ย. 2026): ไม่มีไฟล์จริง 58 passed, 5 skipped (5 = เทสต์ไฟล์จริง) / ชี้ `BHES_SAMPLE_DIR` ไปที่โฟลเดอร์ของไฟล์ Happy Home 63 passed (ถ้าชี้ผิดโฟลเดอร์ เทสต์จะถูกข้ามเงียบ ๆ)
เทสต์รันทุกขั้น Validate → Transform → Integrate → Verify ผ่าน S3 จำลองในหน่วยความจำ ทั้งกรณีผ่านและไม่ผ่าน (แถวหาย, มีคอลัมน์พิกัดเกินมา, จำนวนแถว raw ไม่ตรง: Verify ล้มและไม่ publish อะไร)

### 4.9 ลบทรัพยากร (Destroy)
bucket ต้องว่างก่อน (ไม่ได้เปิด `force_destroy` เพื่อกันข้อมูลหาย) lake bucket เปิด versioning จึงต้องลบ**ทุก version** (ใน S3 console ใช้ปุ่ม Empty ของ bucket `bhes-lake-<ACCOUNT_ID>` และ `bhes-athena-results-<ACCOUNT_ID>`)
```bash
terraform -chdir=infra/terraform destroy
```
bucket state (`bhes-tfstate-<ACCOUNT_ID>`) ลบด้วยมือเมื่อไม่ใช้แล้ว

### 4.10 ปัญหาที่พบบ่อย

| อาการ | สาเหตุและวิธีแก้ |
|---|---|
| `terraform init` แจ้ง backend/bucket ไม่พบ | ยังไม่ได้สร้าง state bucket (4.4) หรือชื่อใน `versions.tf` ไม่ตรงบัญชีคุณ |
| Step Functions จบที่ SkipDuplicate ทั้งที่แก้กฎแล้ว | ไฟล์เดิมได้ `batch_id` เดิม ให้รันด้วย `{"batch_id":"<batch_id>","force":true}` หลัง `terraform apply` |
| Athena แจ้ง `Table not found` / `COLUMN_NOT_FOUND` | ยังไม่ได้รัน crawler หรือแก้ schema แล้วยังไม่ crawl ใหม่ รัน `aws glue start-crawler --name bhes-curated` |
| `pip install pyarrow` ค้างหรือล้มเหลว | ใช้ Python 3.11–3.14 (เราพบปัญหากับ 3.15) |
| `ingest.py` แจ้ง `missing <ชื่อไฟล์>` | ชื่อไฟล์/โฟลเดอร์ใน `data/` ไม่ตรงตาม 4.2 |
| SoVI ล้มที่ ValidationFailed | เป็นพฤติกรรมที่ตั้งใจ (ยังไม่มีกฎ Validate ของ SoVI) |

---

## 5. รายละเอียดการทำงานของ pipeline

ผลลัพธ์ของแต่ละ batch (กฎและเหตุผลอยู่ใน [reports/validation_rules.md](reports/validation_rules.md)):

| ขั้น | โค้ด | เขียนที่ |
|---|---|---|
| Validate | `lambdas/validate/` | `quarantine/<source>/<batch_id>/` : `dq_report.json`, `violations.csv`, `rows.jsonl` (แถวที่ถูกแยก), `manifest.json` |
| Transform | `lambdas/transform/` | `trusted/happy_home/batch_id=<batch_id>/part-0.parquet` (ไม่มีพิกัด ชื่อ หรือรหัสผู้สัมภาษณ์) |
| Integrate | `lambdas/integrate/` | `curated/_pipeline/staging/<batch_id>/happy_home_household.parquet` (รวม risk score T13) |
| Verify | `lambdas/verify/` | ผ่าน: `curated/happy_home_household/part-0.parquet` + `curated/_pipeline/success/<batch_id>/_SUCCESS.json`; ไม่ผ่าน: workflow ล้มพร้อมเหตุผล ไม่ publish |
| CheckBatch | `lambdas/check_batch/` | อ่านอย่างเดียว: เจอ `_SUCCESS.json` ของ batch นั้นแล้วข้ามไป SkipDuplicate |

- **รัน batch เดิมซ้ำ:** ไม่เขียนอะไรซ้ำ batch ที่ล้มกลางทางไม่มี `_SUCCESS.json` จึงรันใหม่ได้ ทุกขั้นเขียนทับ key เดิม
- **แก้กฎหรือเกณฑ์:** แก้ใน `lambdas/common/contracts/` (ชื่อคอลัมน์จริง, ค่าที่อนุญาต, เกณฑ์, schema ของ trusted/curated) แล้ว `terraform apply` และรันไฟล์เดิมด้วย `"force": true`
- **ทดสอบว่า workflow หยุดที่ขั้นที่ล้มเหลว:** ใส่ `"fail_at":"transform"` ใน input (ใช้ได้ทุกขั้น)
- Transform, Integrate, Verify ใช้ pyarrow จาก Lambda layer ของ AWS (AWS SDK for pandas) ส่วน Validate ใช้ Python standard library อย่างเดียว

**ทดสอบบน AWS จริง** (12 พ.ย. 2026, `ap-southeast-1`):

| การรัน | ผล |
|---|---|
| `{"batch_id":"happy_home-26cba344f87c"}` | SUCCEEDED ผ่านทุกขั้น; ผ่าน 88 ถูกแยก 0; trusted/curated ตรงกับผลในเครื่อง |
| batch เดิมซ้ำ | SUCCEEDED ที่ SkipDuplicate (ไม่เขียนซ้ำ) |
| batch เดิม + `"force":true` | SUCCEEDED ผ่านทุกขั้นอีกรอบ ไม่มีไฟล์ซ้ำ |
| `{"batch_id":"sovi-7fb4858da401"}` | FAILED ที่ ValidationFailed (ตั้งใจ) |
| `"fail_at":"check_batch"` | FAILED ที่ CheckBatch ตามที่สั่ง |
| Glue crawler + Athena | ได้ตาราง `happy_home_household` 1 ตาราง (ไม่รวม `_pipeline/`); `count(*)` = 88, ภาระค่าไฟ สูง 35 / อาจสูง 31 / ต่ำ 22 |
| รันใหม่พร้อมคอลัมน์รายข้อ (#24) | SUCCEEDED Verify ผ่าน 88 แถว ตารางมี 53 คอลัมน์ รัน SQL 30 คำสั่งสำเร็จ |

---

## 6. ทรัพยากร AWS และสิทธิ์

Region `ap-southeast-1` (Singapore) ทุก bucket เปิด Block Public Access ครบ 4 ข้อ

| Bucket | ใช้ทำอะไร |
|---|---|
| `bhes-lake-<ACCOUNT_ID>` | data lake: `incoming/`, `raw/`, `quarantine/`, `trusted/`, `curated/` (versioning เปิด) |
| `bhes-athena-results-<ACCOUNT_ID>` | ผลลัพธ์ query ของ Athena |
| `bhes-tfstate-<ACCOUNT_ID>` | Terraform state (สร้างด้วยมือครั้งเดียว) |

| IAM | ใช้โดย | สิทธิ์ |
|---|---|---|
| `bhes-lambda` (role) | Lambda ทุกขั้น | อ่าน `raw/` อย่างเดียว (เขียน/ลบไม่ได้), อ่าน/เขียน `quarantine/` `trusted/` `curated/`, CloudWatch Logs |
| `bhes-sfn` (role) | Step Functions | เรียก Lambda ชื่อ `bhes-*` |
| `bhes-glue-crawler` (role) | Glue Crawler | อ่าน `curated/` อย่างเดียว |
| `bhes-athena-query` (policy) | ผู้ใช้ / QuickSight ที่จะ query | Athena workgroup `bhes-*`, อ่าน Glue catalog + `curated/`, เขียนผลลง athena-results bucket |

| Pipeline | ชื่อ |
|---|---|
| Lambda (log อยู่ CloudWatch `/aws/lambda/<ชื่อ>`) | `bhes-check-batch`, `bhes-validate`, `bhes-transform`, `bhes-integrate`, `bhes-verify` |
| Step Functions | `bhes-pipeline`: CheckBatch → AlreadyDone? → Validate → Valid? → Transform → Integrate → Verify |
| Glue | database `bhes`, crawler `bhes-curated` (1 โฟลเดอร์ใต้ `curated/` = 1 ตาราง) |
| Athena | workgroup `bhes-wg` (จำกัด 1 GB ต่อ query) |

### ข้อควรรู้เรื่อง AWS
- Thailand (`ap-southeast-7`) มี S3, Lambda, Step Functions, Glue, Athena และ CloudWatch แต่ **ไม่มี QuickSight** โครงการจึงใช้ Singapore ทุกคนในทีมต้องตั้ง Region เดียวกัน
- Athena และ QuickSight มีค่าใช้จ่าย ควรตั้ง Budget alert และเช็กราคาก่อนใช้
- ห้ามใช้ root access key ในงานประจำ และห้ามเก็บ access key หรือ `*.tfstate` ใน repo

---

## 7. โครงสร้าง repo

```
README.md                          ภาพรวมโครงการและวิธีรัน (ไฟล์นี้)
architecture/                      Architecture diagram (.drawio.svg ต้นฉบับ + .png) และวิธีแก้ไข
infra/terraform/                   Terraform ของทรัพยากร AWS ทั้งหมด (S3, IAM, Lambda, Step Functions, Glue, Athena)
lambdas/
  <step>/handler.py                โค้ด Lambda แต่ละขั้น (check_batch, validate, transform, integrate, verify)
  common/                          โค้ดที่ทุกขั้นใช้ร่วม + contracts/ (กฎ, ชื่อคอลัมน์จริง, schema ของ trusted/curated)
scripts/
  ingest.py                        นำไฟล์จาก data/ เข้า S3 raw/ พร้อม metadata (รันซ้ำไม่เกิดข้อมูลซ้ำ)
  profile_codebook.py              ตรวจ codebook รันซ้ำได้
  gee_lst.py                       LST ระดับชุมชนจาก Landsat ผ่าน Earth Engine (ทางเลือก ต้อง authenticate ยังไม่ได้รันจริง)
dashboard/
  index.html                       หน้า dashboard ไฟล์เดียว (ผลลัพธ์ของ build.py)
  template.html, build.py          เทมเพลตและสคริปต์สร้างหน้าจาก analytics/results/*.csv
analytics/
  q1_*.sql q2_*.sql q3_*.sql       SQL บน Athena ตอบ Q1–Q3 (+ data_quality.sql)
  run_athena.py                    รันทุกคำสั่งและเก็บ CSV ต่อคำสั่ง
  results/{q1,q2,q3,data_quality}/ ผล CSV (ซ่อน n < 5 แล้ว)
  recheck_local.py                 คำนวณใหม่จากไฟล์ดิบด้วยโค้ดแยกจาก pipeline
  compare_athena_local.py          เทียบผล Athena กับการคำนวณซ้ำ
  significance.py                  Fisher exact จากเซลล์ที่แสดงอยู่
reports/
  data_dictionary.md               ผลตรวจ codebook (#14)
  validation_rules.md              กฎ Validate/Transform และเกณฑ์ D1–D7 (#19, #20, #22)
  integration_feasibility.md       ผลตรวจการเชื่อม SoVI / Happy Home / GEE (#23)
  q1_q3_findings.md                ผลวิเคราะห์ Q1–Q3 (#24)
  crosswalk_sovi_happyhome.csv     ตารางจับคู่ตัวแปรระหว่างสองแบบสำรวจ
  *_variables.csv, profile_summary.json   รายการตัวแปร (เฉพาะค่ารวม ไม่มีข้อมูลรายแถว)
tests/                             เทสต์อัตโนมัติของ pipeline (pytest)
Docs/                              Proposal และแผนแก้ไข (ไฟล์อื่นใน Docs/ ไม่ track)
data/                              ข้อมูลสำรวจดิบ (ในเครื่องเท่านั้น อยู่ใน .gitignore)
```

---

## 8. ข้อค้นพบจากการตรวจข้อมูล

ผลตรวจ codebook (การ์ด #14) รายละเอียดเต็มอยู่ใน [reports/data_dictionary.md](reports/data_dictionary.md)

- **Q1/Q2 ตอบจาก Happy Home ชุดเดียว** SoVI ไม่มีค่าไฟ เครื่องใช้ไฟฟ้า หรือตัวแปรความร้อน (ครอบคลุมน้ำท่วมและภัยแล้ง) จึงใช้เป็นบริบทของ Q3
- **ความร้อนแยกจากน้ำท่วมได้ในโครงสร้างแบบสอบถาม** แต่คำตอบของสองภัยสอดคล้องกันมาก แยกเชิงสถิติได้ยาก
- **รายได้และค่าไฟเป็นช่วง (band) รายเดือน** จึงรายงานภาระค่าไฟเป็นช่วงต่ำสุด–สูงสุด ไม่ใช่ค่าเดียว
- Happy Home มี **88 แถว** (ประกาศไว้ ~81) ชื่อชุมชนมี 16 รูปแบบ (จริง 2 ชุมชน) ต้อง normalise
- Happy Home **มีพิกัดครัวเรือน** (ปัด ≈ 100 ม.) ต้องตัดออกก่อนเข้า Trusted และห้ามเผยแพร่
- ตัวแปรอธิบายของ Q1 แปรผันน้อย (เช่น ไม่มีฉนวน 81/88, ร้อนมากทุกวัน 68/88) ผลจึงอาจออกมาเป็น "ยังไม่เพียงพอ" ซึ่งยอมรับได้ตามสเปก

---

## 9. สถานะงาน

| สถานะ | รายการ |
|---|---|
| ทำแล้ว | ข้อมูลสำรวจ (#13), ตรวจ codebook (#14), Architecture diagram (#15), Terraform S3/IAM (#16) และ Step Functions/Lambda/Glue/Athena (#17), Ingestion (#18), Validate + Quarantine (#19), Transform → Trusted (#20), Idempotency (#21), Verify + เทสต์ (#22), ตรวจการเชื่อม SoVI/Happy Home/GEE (#23), Glue + Athena ตอบ Q1–Q3 (#24), แก้ Proposal (#26) |
| กำลังทำ | README วิธีรัน + บันทึกการใช้ AI (#27), สไลด์และ Demo Checkpoint (#28) |
| ทางเลือก ยังไม่เริ่ม | QuickSight (#33: มีค่าใช้จ่ายรายเดือน รอตัดสินใจ), รัน `scripts/gee_lst.py` จริง |
| ทำแล้ว (PR) | Dashboard Q1–Q3 แบบ HTML ไฟล์เดียวจากผล Athena (`dashboard/`) |

- ภาพ Architecture เป็นดีไซน์เป้าหมายของ Checkpoint ถ้าตอนสร้างจริงต่างจากภาพ ให้แก้ภาพตาม
- งานติดตามใน GitHub Issues และ Project board ของ repo

---

## 10. สมาชิกทีม

| ชื่อ | รหัสนักศึกษา |
|---|---|
| นาย ศุภณัฐ จันทร์เลข | 6709616897 |
| นาย จักรพงษ์ ปักษา | 6709540055 |
| นาย พรินทาน หนุนชู | 6709616673 |
| นาย บริวัฒน์ สงนุ้ย | 6709681107 |

หลักฐานการมีส่วนร่วมรายคนตรวจสอบได้จาก GitHub: Issues (ผู้รับผิดชอบตามการ์ด), Pull Requests และ commit history (`git shortlog -sn --no-merges`)

---

## 11. บันทึกการใช้ AI

หลักการ (CLO6: ใช้ AI อย่างรับผิดชอบ)
1. AI เป็นผู้ช่วย **ทีมเป็นผู้รับผิดชอบงานและข้อสรุปทั้งหมด** ทุกอย่างที่ AI เขียนต้องถูกรันและตรวจ และเข้าทาง Pull Request ก่อน merge
2. **ไม่นำข้อมูลดิบขึ้น GitHub** ข้อมูลสำรวจเป็นไฟล์ anonymized ที่ผู้สอนให้ AI (Claude Code) ทำงานบนเครื่องของผู้ใช้ อ่านไฟล์ด้วยสคริปต์ในเครื่อง และเห็นค่ารวม/ตัวเลขนับระหว่างสำรวจ (รวมกลุ่มเล็กบางค่า) แต่ไม่ได้ดูรหัสครัวเรือนหรือพิกัดรายแถว ไฟล์ที่ commit มีเฉพาะค่ารวมที่ซ่อน n < 5
3. **ไม่เชื่อผลของ AI โดยไม่ตรวจ** ผลวิเคราะห์ต้องมีการคำนวณซ้ำด้วยโค้ดแยกอีกชุด และสิ่งที่ยังไม่ได้ทดสอบต้องบอกตรง ๆ ในเอกสาร
4. การกระทำที่กระทบ AWS (เช่น `terraform apply`) ผู้ใช้เป็นคนสั่งเอง
5. commit และ PR ของทีมไม่ใส่ชื่อ AI เป็นผู้ร่วมเขียน หน้านี้เป็นที่บันทึกการใช้ AI

### บันทึกที่ผู้ใช้ยืนยันได้ (เซสชัน Claude Code ของ `suphanatchanlek30`, 11–12 พ.ย. 2026)

| งาน | AI ช่วยทำอะไร | สิ่งที่ตรวจและผู้รับผิดชอบ |
|---|---|---|
| สรุปสถานะงานของทีม (ตรวจ issue/commit/โค้ดบน `dev`) | อ่าน repo และ GitHub เพื่อสรุปว่าอะไรเสร็จ/เหลือ | สรุปอิงโค้ดและ issue บน `dev` ณ เวลานั้น (ไม่ได้ตรวจว่า deploy บน AWS แล้วหรือยัง) |
| ผลตรวจ #23 (`reports/integration_feasibility.md`, `crosswalk_sovi_happyhome.csv`) | ตรวจ join key, ช่วงเวลา, พิกัด และจับคู่ตัวแปรสองแบบสำรวจจากไฟล์จริง เขียนรายงาน | ตัวเลขทุกตัวมาจากข้อมูลจริงในเครื่อง (ซ่อน n < 5) merge แล้วใน PR #44 ข้อที่ยังไม่ยืนยัน (CRS, ความหมายรหัสพื้นที่ SoVI) ระบุไว้ในรายงาน |
| `scripts/gee_lst.py` | เขียนสคริปต์ดึง LST ระดับชุมชน | **ยังไม่ได้รันกับ Earth Engine** ผ่านแค่การตรวจ syntax สูตรแปลงค่ายังไม่เทียบเอกสาร USGS (ระบุในสคริปต์และรายงาน) |
| คอลัมน์รายข้อใน curated contract (#24) | เสนอและเพิ่ม 15 คอลัมน์ใน `curated_happy_home_household.json` | `pytest` ผ่าน 58; ผู้ใช้รัน `terraform plan` / `apply` เอง; Verify ผ่านบน AWS จริง; แจ้งเพื่อนใน PR #46 เพราะแตะ contract ของ #19–#22 |
| SQL บน Athena และ `analytics/*.py` (#24) | เขียน SQL 30 คำสั่ง สคริปต์รัน/ตรวจซ้ำ และทดสอบ Fisher exact | รันบน Athena จริง; ผลตรงกับ `recheck_local.py` ที่คำนวณจากไฟล์ดิบด้วยโค้ดแยก 174 เซลล์ ต่างกัน 0; ตรวจว่าไม่มีเซลล์ 1–4 หลุด (482 ช่อง); ความต่างที่เจอครั้งแรกเป็นบั๊กของสคริปต์เทียบและแก้แล้ว |
| `reports/q1_q3_findings.md` | ร่างข้อสรุป สนับสนุน/ขัดแย้ง/ยังไม่เพียงพอ และข้อจำกัด | ตัวเลขทุกตัวตรวจกลับไปที่ CSV ผล Athena; ข้อสรุปเป็นความสัมพันธ์ ไม่ใช่เหตุและผล; merge แล้วใน PR #46 |
| README นี้ (#27) | จัดโครงสร้างและเขียนวิธีรัน ตารางทีม และบันทึกนี้ | ชื่อคำสั่ง/ไฟล์/ค่าต่าง ๆ ตรวจกับโค้ดและผลรันจริงของทีม |
| PR และคอมเมนต์ปิดการ์ด #23, #24 | ร่างข้อความ | ผู้ใช้สั่งโพสต์และ merge เอง |

### บันทึกของสมาชิกคนอื่น
ส่วนนี้ **ต้องให้เจ้าของงานเติมเอง** ว่าใช้ AI กับงานใดบ้าง (เช่น `charkpongpaksa` กับ #19/#20/#22, `Meammi` กับ #16–#18) และตรวจอะไรเอง ผู้เขียนหน้านี้ไม่ทราบและไม่ได้สันนิษฐานแทน

| สมาชิก | งานที่ใช้ AI | AI ช่วยทำอะไร | สิ่งที่ตรวจเอง |
|---|---|---|---|
| `Meammi` | _(รอเติม)_ | | |
| `charkpongpaksa` | _(รอเติม)_ | | |
| `Printan00` | _(รอเติม)_ | | |

---

## 12. ข้อตกลงของทีม
- **Git flow:** สร้าง branch → Pull Request เข้า `dev` → `dev` → `main`
- **ความเป็นส่วนตัว:** ห้าม commit ข้อมูลดิบ พิกัด รหัสครัวเรือน access key หรือ `*.tfstate` ตัวเลขที่รายงานซ่อนเซลล์ n < 5 (แสดง `<5`)
- **ภาษาของผล:** ใช้ "สัมพันธ์กับ" ไม่ใช้ "ทำให้" ผลทั้งหมดเป็นความสัมพันธ์
- **ติดตามงาน:** GitHub Issues และ Project board ของ repo

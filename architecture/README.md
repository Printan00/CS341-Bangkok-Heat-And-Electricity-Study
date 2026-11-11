# Architecture diagram (Checkpoint)

[![BHES architecture](bhes_architecture_v2.png)](bhes_architecture_v2.png)

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| `bhes_architecture_v2.drawio.svg` | **ไฟล์ต้นฉบับ** เปิดแก้ใน draw.io ได้ (https://app.diagrams.net → File → Open from → Device) และเปิดดูในเบราว์เซอร์ได้ |
| `bhes_architecture_v2.png` | ภาพสำหรับแสดงใน README / ใส่สไลด์ (เรนเดอร์จากไฟล์ต้นฉบับด้วย Chrome) |

## วิธีอัปเดตภาพ
1. เปิด `bhes_architecture_v2.drawio.svg` ใน draw.io แก้ แล้วบันทึกทับ (File → Export as → SVG และติ๊ก *Include a copy of my diagram*)
2. Export PNG ใหม่ทับ `bhes_architecture_v2.png` (File → Export as → PNG)
3. commit ไฟล์ทั้งสองพร้อมกัน

## อ่านภาพ
- เส้นทางหลัก: แบบสำรวจ → Ingest → Raw → Validate (ไม่ผ่าน → Quarantine) → Transform → Trusted → Integrate → Curated → Verify → Glue + Athena → Evidence report
- วงกลมเลข 1–10 ตรงกับคำอธิบายใต้ภาพ
- **เส้นประมีเส้นเดียว:** Athena → QuickSight (ทางเลือก ไม่มี QuickSight ใน Region Thailand และมีค่าใช้จ่าย)
- ไอคอน AWS ใช้ไลบรารี `mxgraph.aws4` ในตัว draw.io ส่วน GitHub, Terraform ฯลฯ เป็นกล่องข้อความ

"""Demo data — anonymized pharmaceutical business daily reports."""
import datetime
import logging
from src.db import get_session, init_db
from src.models.customer import Customer
from src.models.daily_report import DailyReport
from src.models.literature import MedicalQuestion, LiteratureArticle
from src.models.merge_log import MergeLog

logger = logging.getLogger(__name__)

TODAY = datetime.date.today()

DEMO_CUSTOMERS = [
    {"customer_id": "C001", "department": "心内科", "notes": "科室主任，关注降压药物新进展"},
    {"customer_id": "C002", "department": "肿瘤科", "notes": "学术型客户，经常提问靶向药物问题"},
    {"customer_id": "C003", "department": "内分泌科", "notes": "糖尿病专科"},
    {"customer_id": "C004", "department": "神经内科", "notes": "关注脑血管药物安全性"},
    {"customer_id": "C005", "department": "心内科", "notes": ""},
    {"customer_id": "C006", "department": "肿瘤科", "notes": "年轻医师，关注免疫治疗"},
    {"customer_id": "C007", "department": "呼吸科", "notes": "关注哮喘和COPD治疗方案"},
    {"customer_id": "C008", "department": "内分泌科", "notes": "关注GLP-1受体激动剂"},  # Potential duplicate of C003
]

DEMO_REPORTS = [
    # May 2026
    {"date": "2026-05-05", "department": "心内科", "customer_id": "C001",
     "topic": "新产品降压药介绍", "feedback": "对临床试验数据感兴趣，特别是亚洲人群数据",
     "follow_up_task": "发送亚洲人群亚组分析文献", "task_deadline": "2026-05-12",
     "follow_up_status": "completed", "medical_question": "该降压药在老年高血压患者中的安全性数据如何？",
     "activity_name": "科室会"},
    {"date": "2026-05-07", "department": "肿瘤科", "customer_id": "C002",
     "topic": "PD-1抑制剂最新临床进展", "feedback": "关注联合用药方案的疗效",
     "follow_up_task": "整理联合用药临床数据", "task_deadline": "2026-05-20",
     "follow_up_status": "completed", "medical_question": "PD-1抑制剂联合化疗与单药治疗的疗效对比？",
     "activity_name": "一对一拜访"},
    {"date": "2026-05-08", "department": "内分泌科", "customer_id": "C003",
     "topic": "GLP-1受体激动剂临床应用", "feedback": "对减重效果表示认可，询问医保覆盖",
     "follow_up_task": "查询各地医保政策更新", "task_deadline": "2026-05-22",
     "follow_up_status": "pending", "medical_question": "GLP-1受体激动剂的长期心血管安全性？",
     "activity_name": "科室会"},
    {"date": "2026-05-09", "department": "神经内科", "customer_id": "C004",
     "topic": "抗血小板药物新选择", "feedback": "对出血风险比较关注",
     "follow_up_task": "提供风险对比数据", "task_deadline": "2026-05-15",
     "follow_up_status": "completed", "medical_question": "",
     "activity_name": ""},
    {"date": "2026-05-10", "department": "心内科", "customer_id": "C001",
     "topic": "血压管理新指南解读", "feedback": "新指南的目标值需要更多临床验证",
     "follow_up_task": "整理新指南关键变化点", "task_deadline": "2026-05-18",
     "follow_up_status": "completed", "medical_question": "2026年高血压指南有哪些主要更新？",
     "activity_name": "学术会议"},
    {"date": "2026-05-12", "department": "肿瘤科", "customer_id": "C006",
     "topic": "免疫检查点抑制剂不良反应管理", "feedback": "需要更系统的管理方案",
     "follow_up_task": "整理不良反应管理流程", "task_deadline": "2026-05-25",
     "follow_up_status": "pending", "medical_question": "免疫相关不良反应的预测生物标志物有哪些？",
     "activity_name": "一对一拜访"},
    {"date": "2026-05-14", "department": "呼吸科", "customer_id": "C007",
     "topic": "新型吸入制剂使用培训", "feedback": "装置操作简便性需要改进",
     "follow_up_task": "反馈装置改进建议给产品部", "task_deadline": "2026-05-21",
     "follow_up_status": "cancelled", "medical_question": "",
     "activity_name": "产品培训"},
    {"date": "2026-05-15", "department": "内分泌科", "customer_id": "C008",
     "topic": "糖尿病综合管理方案", "feedback": "关注患者长期依从性问题",
     "follow_up_task": "收集患者教育材料", "task_deadline": "2026-05-30",
     "follow_up_status": "pending", "medical_question": "GLP-1受体激动剂在肥胖非糖尿病患者中的应用前景？",
     "activity_name": "科室会"},
    {"date": "2026-05-16", "department": "心内科", "customer_id": "C005",
     "topic": "血脂管理新进展", "feedback": "PCSK9抑制剂价格偏高",
     "follow_up_task": "了解慈善援助项目", "task_deadline": "2026-05-23",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": ""},
    {"date": "2026-05-18", "department": "肿瘤科", "customer_id": "C002",
     "topic": "CAR-T治疗最新进展", "feedback": "对实体瘤应用很感兴趣",
     "follow_up_task": "查找CAR-T实体瘤文献", "task_deadline": "2026-06-01",
     "follow_up_status": "pending", "medical_question": "CAR-T细胞治疗在实体瘤中的最新临床试验结果？",
     "activity_name": "学术沙龙"},
    {"date": "2026-05-20", "department": "神经内科", "customer_id": "C004",
     "topic": "卒中二级预防新策略", "feedback": "抗凝治疗选择需要个体化",
     "follow_up_task": "", "task_deadline": None,
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": ""},
    {"date": "2026-05-22", "department": "心内科", "customer_id": "C005",
     "topic": "心衰管理新药物", "feedback": "SGLT2抑制剂在心衰中的应用值得关注",
     "follow_up_task": "整理SGLT2抑制剂心衰数据", "task_deadline": "2026-05-29",
     "follow_up_status": "completed", "medical_question": "",
     "activity_name": "科室会"},
    {"date": "2026-05-25", "department": "呼吸科", "customer_id": "C007",
     "topic": "哮喘生物制剂选择", "feedback": "需要更清晰的生物标志物指导",
     "follow_up_task": "整理生物标志物指导路径", "task_deadline": "2026-06-05",
     "follow_up_status": "pending", "medical_question": "重度哮喘生物制剂选择的生物标志物有哪些？",
     "activity_name": "一对一拜访"},
    {"date": "2026-05-27", "department": "肿瘤科", "customer_id": "C006",
     "topic": "ADC药物临床进展", "feedback": "认为ADC是未来重要方向",
     "follow_up_task": "关注ADC领域新批药物", "task_deadline": "2026-06-10",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": ""},
    {"date": "2026-05-28", "department": "内分泌科", "customer_id": "C003",
     "topic": "胰岛素周制剂进展", "feedback": "一周一次注射方案可提高依从性",
     "follow_up_task": "了解国内审批进度", "task_deadline": "2026-06-15",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": "产品介绍"},

    # June 2026
    {"date": "2026-06-01", "department": "心内科", "customer_id": "C001",
     "topic": "心脏康复项目合作", "feedback": "愿意参与多中心研究",
     "follow_up_task": "准备合作协议草案", "task_deadline": "2026-06-10",
     "follow_up_status": "completed", "medical_question": "",
     "activity_name": "项目洽谈"},
    {"date": "2026-06-03", "department": "肿瘤科", "customer_id": "C002",
     "topic": "双特异性抗体进展", "feedback": "对血液肿瘤数据印象深刻",
     "follow_up_task": "整理双特异性抗体对比数据", "task_deadline": "2026-06-17",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": "学术会议"},
    {"date": "2026-06-04", "department": "内分泌科", "customer_id": "C008",
     "topic": "糖尿病足管理新方案", "feedback": "多学科协作模式值得推广",
     "follow_up_task": "联系相关科室组建MDT", "task_deadline": "2026-06-20",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": ""},
    {"date": "2026-06-05", "department": "神经内科", "customer_id": "C004",
     "topic": "阿尔茨海默病新疗法", "feedback": "对早期干预表示认同",
     "follow_up_task": "发送生物标志物检测方案", "task_deadline": "2026-06-12",
     "follow_up_status": "completed", "medical_question": "",
     "activity_name": "科室会"},
    {"date": "2026-06-08", "department": "呼吸科", "customer_id": "C007",
     "topic": "COPD三联疗法对比", "feedback": "需要更多中国人群数据",
     "follow_up_task": "查找中国人群COPD研究", "task_deadline": "2026-06-22",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": ""},
    {"date": "2026-06-09", "department": "心内科", "customer_id": "C005",
     "topic": "抗心律失常药物新选择", "feedback": "安全性是关键考量",
     "follow_up_task": "", "task_deadline": None,
     "follow_up_status": "pending", "medical_question": "新型抗心律失常药物的致心律失常风险？",
     "activity_name": "一对一拜访"},
    {"date": "2026-06-10", "department": "肿瘤科", "customer_id": "C006",
     "topic": "液体活检临床应用", "feedback": "技术成熟度仍需提高",
     "follow_up_task": "整理液体活检灵敏度数据", "task_deadline": "2026-06-24",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": "学术沙龙"},
    {"date": "2026-06-12", "department": "心内科", "customer_id": "C001",
     "topic": "远程心电监测项目", "feedback": "患者接受度良好",
     "follow_up_task": "扩大试点规模方案", "task_deadline": "2026-06-30",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": "项目随访"},
    {"date": "2026-06-15", "department": "内分泌科", "customer_id": "C003",
     "topic": "CGM连续血糖监测", "feedback": "成本问题需要解决",
     "follow_up_task": "了解医保覆盖和政策趋势", "task_deadline": "2026-06-28",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": ""},
    {"date": "2026-06-16", "department": "神经内科", "customer_id": "C004",
     "topic": "偏头痛预防新方案", "feedback": "CGRP拮抗剂临床效果好",
     "follow_up_task": "提供CGRP产品对比资料", "task_deadline": "2026-06-23",
     "follow_up_status": "completed", "medical_question": "",
     "activity_name": "产品介绍"},
    {"date": "2026-06-17", "department": "肿瘤科", "customer_id": "C002",
     "topic": "肿瘤精准医学进展", "feedback": "基因检测指导用药是趋势",
     "follow_up_task": "联系基因检测合作方", "task_deadline": "2026-07-01",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": ""},
    {"date": "2026-06-19", "department": "心内科", "customer_id": "C005",
     "topic": "房颤综合管理", "feedback": "左心耳封堵技术值得关注",
     "follow_up_task": "", "task_deadline": None,
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": "科室会"},
    {"date": "2026-06-20", "department": "呼吸科", "customer_id": "C007",
     "topic": "间质性肺病新进展", "feedback": "抗纤维化药物选择有限",
     "follow_up_task": "关注新药临床试验", "task_deadline": "2026-07-05",
     "follow_up_status": "pending", "medical_question": "新型抗纤维化药物的作用机制？",
     "activity_name": ""},
    {"date": "2026-06-22", "department": "内分泌科", "customer_id": "C008",
     "topic": "甲状腺结节管理指南", "feedback": "细针穿刺指征需要统一标准",
     "follow_up_task": "", "task_deadline": None,
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": "科室会"},
    {"date": "2026-06-24", "department": "肿瘤科", "customer_id": "C006",
     "topic": "肿瘤疫苗研发进展", "feedback": "个体化疫苗是未来方向",
     "follow_up_task": "整理肿瘤疫苗文献综述", "task_deadline": "2026-07-08",
     "follow_up_status": "pending", "medical_question": "",
     "activity_name": "学术会议"},
]

DEMO_MEDICAL_QUESTIONS = [
    {"question_text": "该降压药在老年高血压患者中的安全性数据如何？", "search_zh": '["降压药", "老年高血压", "安全性"]',
     "search_en": '["antihypertensive", "elderly hypertension", "safety"]'},
    {"question_text": "PD-1抑制剂联合化疗与单药治疗的疗效对比？", "search_zh": '["PD-1抑制剂", "联合化疗", "疗效对比"]',
     "search_en": '["PD-1 inhibitor", "combination chemotherapy", "efficacy comparison"]'},
    {"question_text": "GLP-1受体激动剂的长期心血管安全性？", "search_zh": '["GLP-1受体激动剂", "心血管安全性", "长期"]',
     "search_en": '["GLP-1 receptor agonist", "cardiovascular safety", "long-term"]'},
    {"question_text": "CAR-T细胞治疗在实体瘤中的最新临床试验结果？", "search_zh": '["CAR-T", "实体瘤", "临床试验"]',
     "search_en": '["CAR-T cell therapy", "solid tumor", "clinical trial"]'},
    {"question_text": "免疫相关不良反应的预测生物标志物有哪些？", "search_zh": '["免疫治疗", "不良反应", "生物标志物"]',
     "search_en": '["immune-related adverse events", "biomarker", "prediction"]'},
]


def init_demo_data():
    """Initialize demo data if database is empty."""
    session = get_session()
    try:
        existing = session.query(Customer).count()
        if existing > 0:
            logger.info(f"Database already has {existing} customers, skipping demo data init.")
            return

        logger.info("Initializing demo data...")

        # Create customers
        for cdata in DEMO_CUSTOMERS:
            c = Customer(**cdata)
            session.add(c)

        # Create reports
        for rdata in DEMO_REPORTS:
            r = DailyReport(
                date=datetime.date.fromisoformat(rdata["date"]),
                department=rdata["department"],
                customer_id=rdata["customer_id"],
                topic=rdata["topic"],
                feedback=rdata["feedback"],
                follow_up_task=rdata["follow_up_task"] or None,
                task_deadline=datetime.date.fromisoformat(rdata["task_deadline"]) if rdata.get("task_deadline") else None,
                follow_up_status=rdata["follow_up_status"],
                medical_question=rdata["medical_question"] or None,
                activity_name=rdata["activity_name"] or None,
                raw_text=f"[Demo] {rdata['date']} {rdata['department']} {rdata['customer_id']} {rdata['topic']}",
            )
            session.add(r)

        # Create medical questions
        for qdata in DEMO_MEDICAL_QUESTIONS:
            q = MedicalQuestion(
                question_text=qdata["question_text"],
                search_terms_zh=qdata["search_zh"],
                search_terms_en=qdata["search_en"],
            )
            session.add(q)

        session.commit()
        logger.info(f"Demo data initialized: {len(DEMO_CUSTOMERS)} customers, "
                    f"{len(DEMO_REPORTS)} reports, {len(DEMO_MEDICAL_QUESTIONS)} medical questions.")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to init demo data: {e}")
        raise
    finally:
        session.close()

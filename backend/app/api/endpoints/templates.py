from fastapi import APIRouter
from app.services.backtest.templates import STRATEGY_TEMPLATES

router = APIRouter()


@router.get("")
async def list_templates():
    """获取所有内置策略模板"""
    return [
        {
            "id": key,
            "name": t["name"],
            "description": t["description"],
            "params": t["params"],
            "code": t["code"],
        }
        for key, t in STRATEGY_TEMPLATES.items()
    ]


@router.get("/{template_id}")
async def get_template(template_id: str):
    """获取单个策略模板详情"""
    if template_id not in STRATEGY_TEMPLATES:
        return {"error": "模板不存在"}
    t = STRATEGY_TEMPLATES[template_id]
    return {
        "id": template_id,
        "name": t["name"],
        "description": t["description"],
        "params": t["params"],
        "code": t["code"],
    }

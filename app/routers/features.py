"""Feature/plugin router — manage the modular feature registry."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.feature import Feature
from app.models.user import User
from app.schemas.feature import FeatureCreate, FeatureOut, FeatureUpdate
from app.services import plugins

router = APIRouter(prefix="/features", tags=["features"])


@router.get("", response_model=list[FeatureOut])
def list_features(
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Feature]:
    query = db.query(Feature).order_by(Feature.name.asc())
    if enabled_only:
        query = query.filter(Feature.enabled.is_(True))
    return query.all()


@router.post("", response_model=FeatureOut, status_code=status.HTTP_201_CREATED)
def create_feature(
    data: FeatureCreate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> Feature:
    if db.query(Feature).filter(Feature.name == data.name).first():
        raise HTTPException(status_code=400, detail="Feature name already exists")
    return plugins.create_feature(db, data)


@router.get("/{name}", response_model=FeatureOut)
def get_feature(name: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> Feature:
    feature = db.query(Feature).filter(Feature.name == name).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature


@router.patch("/{name}", response_model=FeatureOut)
def update_feature(
    name: str, data: FeatureUpdate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> Feature:
    feature = db.query(Feature).filter(Feature.name == name).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return plugins.update_feature(db, feature, data)


@router.post("/{name}/enable", response_model=FeatureOut)
def enable_feature(name: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> Feature:
    feature = db.query(Feature).filter(Feature.name == name).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return plugins.set_enabled(db, feature, True)


@router.post("/{name}/disable", response_model=FeatureOut)
def disable_feature(name: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> Feature:
    feature = db.query(Feature).filter(Feature.name == name).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return plugins.set_enabled(db, feature, False)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feature(name: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> None:
    feature = db.query(Feature).filter(Feature.name == name).first()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    db.delete(feature)
    db.commit()

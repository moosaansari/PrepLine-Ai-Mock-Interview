import logging
from typing import Any, Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import settings

logger = logging.getLogger(__name__)

_db = None


                                                              
                         
                                                              

def initialize_firebase():
    """
    Initialize Firebase Admin SDK and Firestore.

    Safe to call multiple times.
    """

    global _db

    if _db is not None:
        return _db

    try:
        if firebase_admin._apps:
            _db = firestore.client()

            logger.info("Firebase Firestore connected.")

            return _db

        project_id = settings.FIREBASE_PROJECT_ID
        client_email = settings.FIREBASE_CLIENT_EMAIL
        private_key = settings.FIREBASE_PRIVATE_KEY
        credentials_path = settings.FIREBASE_CREDENTIALS_PATH

        if credentials_path:
                                                                      
                                                                    
                                                                       
                               
            credential = credentials.Certificate(credentials_path)

            firebase_admin.initialize_app(credential)

        else:
            if not project_id:
                raise RuntimeError(
                    "FIREBASE_PROJECT_ID is missing from .env"
                )

            if not client_email:
                raise RuntimeError(
                    "FIREBASE_CLIENT_EMAIL is missing from .env"
                )

            if not private_key:
                raise RuntimeError(
                    "FIREBASE_PRIVATE_KEY is missing from .env"
                )

            private_key = private_key.replace("\\n", "\n")

            service_account_info = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }

            credential = credentials.Certificate(
                service_account_info
            )

            firebase_admin.initialize_app(
                credential,
                {
                    "projectId": project_id,
                },
            )

        _db = firestore.client()

        logger.info(
            "Firebase Firestore initialized successfully."
        )

        return _db

    except Exception as exc:
        logger.exception(
            "Firebase initialization failed: %s",
            exc,
        )

        raise RuntimeError(
            f"Unable to initialize Firebase Firestore: {exc}"
        ) from exc


                                                              
                  
                                                              

def get_db():
    global _db

    if _db is None:
        initialize_firebase()

    return _db


def get_firestore():
    return get_db()


                                                              
                 
                                                              

def create_document(
    collection_name: str,
    data: Dict[str, Any],
    document_id: Optional[str] = None,
) -> Dict[str, Any]:

    db = get_db()

    collection_ref = db.collection(collection_name)

    if document_id:
        document_ref = collection_ref.document(document_id)
    else:
        document_ref = collection_ref.document()

    document_ref.set(data)

    result = dict(data)
    result["id"] = document_ref.id

    return result


                                                              
              
                                                              

def set_document(
    collection_name: str,
    document_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:

    db = get_db()

    document_ref = (
        db.collection(collection_name)
        .document(document_id)
    )

    document_ref.set(data)

    result = dict(data)
    result["id"] = document_id

    return result


                                                              
              
                                                              

def get_document(
    collection_name: str,
    document_id: str,
) -> Optional[Dict[str, Any]]:

    db = get_db()

    document_ref = (
        db.collection(collection_name)
        .document(document_id)
    )

    document = document_ref.get()

    if not document.exists:
        return None

    data = document.to_dict() or {}
    data["id"] = document.id

    return data


                                                              
                
                                                              

def list_documents(
    collection_name: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    order_by: Optional[str] = None,
    descending: bool = False,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:

    db = get_db()

    query = db.collection(collection_name)

    if filters:
        for item in filters:
            field = item.get("field")
            operator = item.get("operator", "==")
            value = item.get("value")

            if not field:
                continue

            query = query.where(
                filter=firestore.FieldFilter(
                    field,
                    operator,
                    value,
                )
            )

    if order_by:
        direction = (
            firestore.Query.DESCENDING
            if descending
            else firestore.Query.ASCENDING
        )

        query = query.order_by(
            order_by,
            direction=direction,
        )

    if limit:
        query = query.limit(int(limit))

    documents = query.stream()

    results = []

    for document in documents:
        data = document.to_dict() or {}
        data["id"] = document.id
        results.append(data)

    return results


                                                              
                 
                                                              

def update_document(
    collection_name: str,
    document_id: str,
    data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:

    db = get_db()

    document_ref = (
        db.collection(collection_name)
        .document(document_id)
    )

    document = document_ref.get()

    if not document.exists:
        return None

    document_ref.update(data)

    updated = document_ref.get()

    result = updated.to_dict() or {}
    result["id"] = document_id

    return result


                                                              
                 
                                                              

def delete_document(
    collection_name: str,
    document_id: str,
) -> bool:

    db = get_db()

    document_ref = (
        db.collection(collection_name)
        .document(document_id)
    )

    document_ref.delete()

    return True


                                                              
                
                                                              

def document_exists(
    collection_name: str,
    document_id: str,
) -> bool:

    db = get_db()

    document = (
        db.collection(collection_name)
        .document(document_id)
        .get()
    )

    return document.exists


                                                              
                  
                                                              

def collection_exists(
    collection_name: str,
) -> bool:

    db = get_db()

    documents = (
        db.collection(collection_name)
        .limit(1)
        .stream()
    )

    return next(documents, None) is not None
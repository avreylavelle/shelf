from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class Repository(ABC):
    @abstractmethod
    def get_all_users(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_user(
        self,
        username: str,
        age: Optional[int] = None,
        gender: str = "",
        preferred_genres: Optional[Dict[str, Any]] = None,
        preferred_themes: Optional[Dict[str, Any]] = None,
        read_manga: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_manga_by_id(self, manga_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_manga_dataset(self) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def search_manga_titles(
        self, query: str, limit: int = 20, lang: str = "en"
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_user_ratings(self, user_id: str) -> List[Tuple[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def upsert_rating(
        self, user_id: str, manga_id: str, rating: Any
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def delete_rating(
        self, user_id: str, manga_id: str
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

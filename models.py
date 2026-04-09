from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    title: str = Field(min_length=1)
    link: str = Field(min_length=1)
    published: str = Field(default="N/A")
    source: str = Field(default="Unknown")
    summary: str = Field(default="")

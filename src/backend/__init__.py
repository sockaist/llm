"""
Langchain 커스텀 구현 라이브러리 - 메인 패키지 파일
"""

from src.prompt import (
    BasePromptTemplate,
    StringPromptTemplate,
    SimplePromptTemplate,
    InstructionConfig
)

from src.output_parsers import (
    BaseOutputParser,
    JSONOutputParser,
    ListOutputParser,
    CommaSeparatedListOutputParser,
    StructuredOutputParser,
    XMLOutputParser,
    RegexParser,
    MarkdownOutputParser,
    CSVOutputParser,
    DatetimeOutputParser,
    CustomFunctionOutputParser,
    CombiningOutputParser,
    AutoFixOutputParser
)

from src.chatbot import ChatBot

from src.chain import (
    Chain,
    LLMChain,
    SequentialChain,
    RouterChain,
    TransformChain
)

from src.memory import (
    Memory,
    BufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
    ConversationTokenBufferMemory
)

try:
    from src.prompt import Jinja2PromptTemplate
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    from src.output_parsers import PydanticOutputParser
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

try:
    from src.output_parsers import YAMLOutputParser
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

__all__ = [
    # 프롬프트 템플릿
    "BasePromptTemplate",
    "StringPromptTemplate",
    "SimplePromptTemplate",
    "InstructionConfig",
    
    # 출력 파서
    "BaseOutputParser",
    "JSONOutputParser",
    "ListOutputParser",
    "CommaSeparatedListOutputParser",
    "StructuredOutputParser",
    "XMLOutputParser",
    "RegexParser",
    "MarkdownOutputParser",
    "CSVOutputParser",
    "DatetimeOutputParser",
    "CustomFunctionOutputParser",
    "CombiningOutputParser",
    "AutoFixOutputParser",
    
    # ChatBot
    "ChatBot",
    
    # 체인
    "Chain",
    "LLMChain",
    "SequentialChain",
    "RouterChain",
    "TransformChain",
    
    # 메모리
    "Memory",
    "BufferMemory",
    "ConversationBufferWindowMemory",
    "ConversationSummaryMemory",
    "ConversationTokenBufferMemory"
]

if JINJA2_AVAILABLE:
    __all__.append("Jinja2PromptTemplate")

if PYDANTIC_AVAILABLE:
    __all__.append("PydanticOutputParser")

if YAML_AVAILABLE:
    __all__.append("YAMLOutputParser")

__version__ = "0.1.0"
__author__ = "Langchain Custom Implementation Team"

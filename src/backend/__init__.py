"""
Langchain 커스텀 구현 라이브러리 - 메인 패키지 파일
"""

# === utils.prompt ===
from ...src.backend.src.utils.prompt import (
    BasePromptTemplate,
    StringPromptTemplate,
    SimplePromptTemplate,
    InstructionConfig
)

# === utils.output_parsers ===
from ...src.backend.src.utils.output_parsers import (
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

# === llm ===
"""
from ...src.backend.src.llm import (
    # QueryMaker,
    # Checker,
    # InputNormalizer,
    # FilterGenerator
)
"""

# === utils.chatbot ===
from ...src.backend.src.utils.chatbot import ChatBot

# === utils.chain ===
from ...src.backend.src.utils.chain import (
    Chain,
    LLMChain,
    SequentialChain,
    RouterChain,
    TransformChain
)

# === utils.memory ===
from ...src.backend.src.utils.memory import (
    Memory,
    BufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
    ConversationTokenBufferMemory
)

# === 선택적 모듈 ===
try:
    from ...src.backend.src.utils.prompt import Jinja2PromptTemplate
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    from ...src.backend.src.utils.output_parsers import PydanticOutputParser
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

try:
    from ...src.backend.src.utils.output_parsers import YAMLOutputParser
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

    # LLM 관련
    # "QueryMaker",
    # "FilterGenerator",
    # "InputChecker",
    # "InputNormalizer",

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
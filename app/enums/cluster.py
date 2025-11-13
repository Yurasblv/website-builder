from app.enums.base import BaseStrEnum


class GenerationStatus(BaseStrEnum):
    """
    Statuses for cluster state.

    STEP1: keyword input with setting amount of nodes
    STEP2: generated structure review
    STEP3: Assigning author
    STEP4: Assigning style parameters to elements
    GENERATING: Generating the content for the pages
    BUILDING: Creating html pages from json files
    GENERATED: All json pages are generated and ready for build
    BUILT: Cluster is built, pages are in html format and can be downloaded in zip format
    GENERATION_FAILED: Error during content generation
    BUILD_FAILED: Error during build
    """

    STEP1 = "STEP1"
    STEP2 = "STEP2"
    STEP3 = "STEP3"
    STEP4 = "STEP4"
    GENERATING = "GENERATING"
    BUILDING = "BUILDING"
    GENERATED = "GENERATED"
    BUILT = "BUILT"
    GENERATION_FAILED = "GENERATION_FAILED"
    BUILD_FAILED = "BUILD_FAILED"

    @classmethod
    def get_step_by_id(cls, v: int) -> BaseStrEnum:
        """Select step by id. Relevant for cluster update during configuring parameters."""
        return [i for i in list(cls.__members__.values()) if i.value.endswith(str(v))][0]

    @classmethod
    def draft_statuses(cls) -> list[BaseStrEnum]:
        """Draft statuses"""
        return cls.able_to_generate_statuses() + [cls.GENERATING]

    @classmethod
    def generated_statuses(cls) -> list[BaseStrEnum]:
        """Statuses for blocking generation of cluster if it has one of following states"""
        return cls.able_to_build_statuses() + [cls.BUILDING, cls.BUILT]

    @classmethod
    def able_to_build_statuses(cls) -> list[BaseStrEnum]:
        """Statuses for starting build of cluster"""
        return [cls.GENERATED, cls.BUILD_FAILED]

    @classmethod
    def able_to_generate_statuses(cls) -> list[BaseStrEnum]:
        """Statuses for starting generation of cluster"""
        return [cls.STEP1, cls.STEP2, cls.STEP3, cls.STEP4, cls.GENERATION_FAILED]

    @classmethod
    def unable_to_restart_statuses(cls) -> list[BaseStrEnum]:
        """Statuses that prevent the deployment"""
        return [cls.GENERATING, cls.BUILDING]

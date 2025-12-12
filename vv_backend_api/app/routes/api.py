from flask_smorest import Blueprint
from flask.views import MethodView
from marshmallow import Schema, fields
from datetime import datetime
from typing import List
from ..db import session_scope, get_db
from ..db.models import SRS, TestCase, Script, Run, TestResult
from ..services import LLMService, ScriptService, ExecutionService, StorageService

blp = Blueprint(
    "V&V API",
    "vv",
    url_prefix="/api",
    description="V&V automation endpoints for SRS upload, generation, execution and reporting",
)

# Schemas
class SRSSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, description="SRS title")
    description = fields.Str(load_default=None, allow_none=True)
    content = fields.Str(load_default=None, allow_none=True)

class TestCaseSchema(Schema):
    id = fields.Int(dump_only=True)
    srs_id = fields.Int(required=True)
    name = fields.Str(required=True)
    description = fields.Str(load_default=None, allow_none=True)
    priority = fields.Str(load_default=None, allow_none=True)
    tags = fields.Str(load_default=None, allow_none=True)

class ScriptSchema(Schema):
    id = fields.Int(dump_only=True)
    test_case_id = fields.Int(required=True)
    language = fields.Str()
    framework = fields.Str()
    content = fields.Str(allow_none=True)
    file_path = fields.Str(allow_none=True)

class RunSchema(Schema):
    id = fields.Int(dump_only=True)
    label = fields.Str(allow_none=True)
    status = fields.Str()
    started_at = fields.DateTime(allow_none=True)
    finished_at = fields.DateTime(allow_none=True)
    triggered_by = fields.Str(allow_none=True)

class TestResultSchema(Schema):
    id = fields.Int(dump_only=True)
    run_id = fields.Int()
    script_id = fields.Int()
    outcome = fields.Str()
    duration_ms = fields.Int(allow_none=True)
    message = fields.Str(allow_none=True)
    artifacts_path = fields.Str(allow_none=True)


@blp.route("/srs")
class SRSCollection(MethodView):
    @blp.arguments(SRSSchema)
    @blp.response(201, SRSSchema)
    def post(self, payload):
        """Create SRS with title/content as JSON body."""
        with session_scope() as db:
            srs = SRS(title=payload["title"], description=payload.get("description"), content=payload.get("content"))
            db.add(srs)
            db.flush()
            return srs

@blp.route("/srs/<int:srs_id>")
class SRSItem(MethodView):
    @blp.response(200, SRSSchema)
    def get(self, srs_id: int):
        """Get SRS by id."""
        with session_scope() as db:
            srs = db.get(SRS, srs_id)
            if not srs:
                return {"message": "Not found"}, 404
            return srs


@blp.route("/testcases/generate")
class TestCaseGeneration(MethodView):
    @blp.arguments(SRSSchema(only=("id",)))
    @blp.response(200, TestCaseSchema(many=True))
    def post(self, payload):
        """Generate test cases for a given SRS id using LLM service."""
        srs_id = payload["id"]
        with session_scope() as db:
            srs = db.get(SRS, srs_id)
            if not srs:
                return {"message": "SRS not found"}, 404
            llm = LLMService()
            cases = llm.generate_test_cases(srs.title, srs.content or "")
            created = []
            for c in cases:
                tc = TestCase(
                    srs_id=srs.id,
                    name=c["name"],
                    description=c.get("description"),
                    priority=c.get("priority"),
                    tags=c.get("tags"),
                )
                db.add(tc)
                db.flush()
                created.append(tc)
            return created

    @blp.response(200, TestCaseSchema(many=True))
    def get(self):
        """List all test cases."""
        db = get_db()
        try:
            return db.query(TestCase).all()
        finally:
            db.close()


@blp.route("/scripts/generate")
class ScriptGeneration(MethodView):
    class GeneratePayload(Schema):
        test_case_id = fields.Int(required=True)

    @blp.arguments(GeneratePayload)
    @blp.response(201, ScriptSchema)
    def post(self, payload):
        """Generate a pytest+Playwright script for a test case."""
        tc_id = payload["test_case_id"]
        with session_scope() as db:
            tc = db.get(TestCase, tc_id)
            if not tc:
                return {"message": "TestCase not found"}, 404
            llm = LLMService()
            script_text = llm.generate_script(
                {"name": tc.name, "description": tc.description, "priority": tc.priority, "tags": tc.tags}
            )
            storage = StorageService()
            ssvc = ScriptService(storage)
            file_path, _ = ssvc.write_script_for_test_case(tc.id, {"name": tc.name}, script_text)
            script = Script(test_case_id=tc.id, language="python", framework="pytest-playwright", content=script_text, file_path=file_path)
            db.add(script)
            db.flush()
            return script

    @blp.response(200, ScriptSchema(many=True))
    def get(self):
        """List all scripts."""
        db = get_db()
        try:
            return db.query(Script).all()
        finally:
            db.close()


@blp.route("/runs")
class Runs(MethodView):
    class RunCreate(Schema):
        label = fields.Str(load_default=None)
        script_ids = fields.List(fields.Int, required=True)
        triggered_by = fields.Str(load_default="api")

    @blp.arguments(RunCreate)
    @blp.response(201, RunSchema)
    def post(self, payload):
        """Create a run and execute provided script ids via pytest."""
        with session_scope() as db:
            run = Run(label=payload.get("label"), status="running", started_at=datetime.utcnow(), triggered_by=payload.get("triggered_by"))
            db.add(run)
            db.flush()

            # collect script paths
            scripts: List[Script] = db.query(Script).filter(Script.id.in_(payload["script_ids"])).all()
            script_paths = [s.file_path for s in scripts if s.file_path]
            exsvc = ExecutionService()
            code, junit_path, log_path = exsvc.run_scripts(run.id, script_paths)

            # Basic parsing of outcome by exit code
            run.status = "completed" if code == 0 else "failed"
            run.finished_at = datetime.utcnow()

            # Create TestResult rows (one per script, rough status based on exit code)
            for s in scripts:
                tr = TestResult(
                    run_id=run.id,
                    script_id=s.id,
                    outcome="passed" if code == 0 else "failed",
                    duration_ms=None,
                    message=f"See junit: {junit_path}",
                    artifacts_path=log_path,
                )
                db.add(tr)
            db.flush()

            return run


@blp.route("/runs/<int:run_id>")
class RunItem(MethodView):
    @blp.response(200, RunSchema)
    def get(self, run_id: int):
        """Get run by id."""
        with session_scope() as db:
            run = db.get(Run, run_id)
            if not run:
                return {"message": "Run not found"}, 404
            return run


@blp.route("/runs/<int:run_id>/results")
class RunResults(MethodView):
    @blp.response(200, TestResultSchema(many=True))
    def get(self, run_id: int):
        """Get test results for a run."""
        db = get_db()
        try:
            return db.query(TestResult).filter(TestResult.run_id == run_id).all()
        finally:
            db.close()


@blp.route("/runs/<int:run_id>/logs")
class RunLogs(MethodView):
    def get(self, run_id: int):
        """Return path to run logs and brief tail."""
        storage = StorageService()
        log_path = storage.run_artifact(run_id, "run.log")
        tail = ""
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                tail = "".join(lines[-100:])
        except FileNotFoundError:
            return {"message": "Log not found"}, 404
        return {"log_path": log_path, "tail": tail}


@blp.route("/reports/latest")
class ReportsLatest(MethodView):
    def get(self):
        """Return the latest run summary."""
        db = get_db()
        try:
            latest = db.query(Run).order_by(Run.created_at.desc()).first()
            if not latest:
                return {"message": "No runs"}, 404
            results = db.query(TestResult).filter(TestResult.run_id == latest.id).all()
            passed = sum(1 for r in results if r.outcome == "passed")
            failed = sum(1 for r in results if r.outcome == "failed")
            return {"run_id": latest.id, "status": latest.status, "passed": passed, "failed": failed, "total": len(results)}
        finally:
            db.close()

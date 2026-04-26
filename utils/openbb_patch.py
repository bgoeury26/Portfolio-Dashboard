import pathlib, tempfile

try:
    import openbb_core.app.static.package_builder as _pb
    _tmp_lock = pathlib.Path(tempfile.gettempdir()) / "openbb.build.lock"
    _orig_build = _pb.PackageBuilder.build
    def _safe_build(self, modules=None):
        self.lock_path = _tmp_lock
        _orig_build(self, modules)
    _pb.PackageBuilder.build = _safe_build
    _orig_autobuild = _pb.PackageBuilder.auto_build
    def _safe_autobuild(self):
        self.lock_path = _tmp_lock
        _orig_autobuild(self)
    _pb.PackageBuilder.auto_build = _safe_autobuild
except Exception:
    pass

import pathlib, tempfile

try:
    import openbb_core.app.static.package_builder as _pb
    _tmp = pathlib.Path(tempfile.gettempdir()) / "openbb.build.lock"
    _orig = _pb.PackageBuilder.__init__
    def _p(self, directory=None, lint=True, verbose=False):
        _orig(self, directory, lint, verbose)
        self.lock_path = _tmp
    _pb.PackageBuilder.__init__ = _p
except Exception:
    pass

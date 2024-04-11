{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.freetype
    pkgs.sqlite
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
  ];
}

# ForgeCLI Homebrew formula.
#
# Preferred install method:  uv tool install forgecli
class Forgecli < Formula
  desc "AI optimization runtime — Graphify, Caveman, , Smart Routing"
  homepage "https://github.com/forgecli/forgecli"
  url "https://files.pythonhosted.org/packages/source/f/forgecli/forgecli-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_REAL_SHA256"
  license "MIT"

  depends_on "python@3.12"

  # Graphify is built in ; 

  def install
    virtualenv_install_with_resources
  end

  def post_install
    ohai "Run `forge init` to complete setup."
  end

  test do
    system bin/"forge", "--version"
    system bin/"forge", "doctor"
  end
end

# ForgeCLI Homebrew formula.
#
# ForgeCLI is a single Python package — Ponytail is built-in and
# Graphify is an optional enhancement.
#
# To install locally while the upstream tap is being set up:
#
#   brew install --build-from-source ./packaging/homebrew/forgecli.rb
#
# To publish to a tap:
#   1. Create a tap repo, e.g. mdshzb04/homebrew-tap
#   2. Copy this file to Formula/forgecli.rb
#   3. Tag a release; update the `url` and `sha256` below.
#
# Preferred install method:  uv tool install forgecli
class Forgecli < Formula
  desc "AI-first developer operating system — orchestrates Graphify, Ponytail (built-in), and any LLM"
  homepage "https://github.com/mdshzb04/ForgeCli"
  url "https://files.pythonhosted.org/packages/source/f/forgecli/forgecli-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_REAL_SHA256"
  license "MIT"

  depends_on "python@3.12"

  # Ponytail is built-in — no separate resource needed.
  # Graphify is optional; install separately with:
  #   uv tool install graphifyy

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

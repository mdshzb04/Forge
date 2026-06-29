# ForgeCLI Homebrew formula.
#
# To install locally while the upstream tap is being set up:
#
#   brew install --build-from-source ./packaging/homebrew/forgecli.rb
#
# To publish to a tap:
#   1. Create a tap repo, e.g. mdshzb04/homebrew-tap
#   2. Copy this file to Formula/forgecli.rb
#   3. Tag a release; update the `url` and `sha256` below.
class Forgecli < Formula
  desc "AI-first developer operating system that orchestrates Graphify, Ponytail, and any LLM"
  homepage "https://github.com/mdshzb04/ForgeCli"
  url "https://files.pythonhosted.org/packages/source/f/forgecli/forgecli-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_REAL_SHA256"
  license "MIT"

  depends_on "python@3.12"

  resource "graphify" do
    url "https://files.pythonhosted.org/packages/source/g/graphify/graphify-0.9.1.tar.gz"
    sha256 "REPLACE_WITH_REAL_SHA256"
  end

  resource "ponytail" do
    url "https://files.pythonhosted.org/packages/source/p/ponytail/ponytail-0.1.0.tar.gz"
    sha256 "REPLACE_WITH_REAL_SHA256"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"forge", "--version"
  end
end

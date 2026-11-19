# Nordic for RustRover and CLion

A RustRover and CLion port of [nordic.nvim](https://github.com/AlexvZyl/nordic.nvim) (default
options: `reduced_blue`, italic comments, no bold keywords), built so that **Rust and C/C++ look
the way they do in Neovim** with treesitter + rust-analyzer / clangd.

- **Nordic** editor color scheme
- **Nordic** Islands UI theme: JetBrains' *Islands Darcula* layout recoloured with the nordic
  palette (optional; the editor scheme works with any UI theme)

## Install

1. Download `nordic-rustrover-1.1.0.jar` from the [latest release](https://github.com/sfra6651/nordic-rustrover/releases/latest).
2. Settings → Plugins → ⚙ → **Install Plugin from Disk…** → select the jar, then restart.
3. Settings → Editor → Color Scheme → **Nordic**
   (or Appearance → Theme → **Nordic** for the UI theme too; it selects the scheme for you).

Requires RustRover or CLion 2025.3+ (Rust keys checked against RustRover 2026.2.4, C/C++ keys
against CLion 2025.3.3). The same jar works in both IDEs.

## How the Rust colours were derived

What you see in Neovim is not just nordic's group table: it's treesitter captures layered
under rust-analyzer semantic tokens, and some nordic groups fall through to Neovim's defaults.
So instead of translating the group table:

1. Neovim (nordic + nvim-treesitter + rust-analyzer) was driven through a real UI client and the
   exact rendered colour of every character was recorded, on code covering every RustRover
   Rust colour key.
2. RustRover's own highlighter classes were read to learn exactly what each `org.rust.*` key
   covers (e.g. the `!` in `println!` is its own key, the whole `#[...]` is one key, `::` shares
   the operator key with `=`).
3. Where RustRover has one key but Neovim shows several colours, the choice was made by measuring
   real-world Rust code (a web backend, a wgpu renderer, a ray tracer).

Simulated on that code, **94% of non-whitespace characters get the identical colour and
italics** as in Neovim.

| RustRover key(s) | Colour | nordic source |
|---|---|---|
| functions, methods, calls | `#88C0D0` blue2 | Function |
| struct, enum, union, type alias, primitive, type param | `#EBCB8B` yellow | Type |
| trait | `#D08770` orange | `@lsp.type.interface` → Keyword |
| keyword, `unsafe` | `#D08770` orange | Keyword |
| field, enum variant | `#8FBCBB` cyan | Field |
| constant, static, const param, number | `#BE9DB8` magenta | Constant |
| module, crate | `#E7C173` yellow.dim | Namespace |
| `self` | `#5E81AC` blue0 | Builtin |
| parameters | fg, *italic* | `@parameter` |
| variables (incl. `mut`, no underline) | `#C0C8D8` fg | Variable |
| macro calls, `macro_rules`, `$x`, attributes, format `{}` | `#BF616A` red | Macro |
| macro `!`, `macro_rules!` name | `#BE9DB8` magenta | `@lsp.type.macro` → Constant |
| lifetime | `#81A1C1` blue1 | `@attribute.builtin` → Special |
| string, char, format arg names | `#A3BE8C` green | String |
| escapes | `#BE9DB8` magenta | `@string.escape` |
| `,` `;` `.` and operators | `#60728A` gray5, *italic* | Delimiter |
| brackets, `?`, overloaded ops, closure bars | fg | Operator |
| all comments incl. doc comments | `#4C566A` gray4, *italic* | Comment |
| `#[cfg]`-disabled code | gray4, *italic* | DiagnosticUnnecessary |

## Known differences (RustRover has one key where Neovim has two colours)

| What | Neovim | RustRover | Why this choice |
|---|---|---|---|
| Operators | `::` `:` `->` `=>` gray italic; `=` `&` `<>` `+` fg | all gray italic | gray group is the larger share of operator characters |
| Enum variants | user/3rd-party cyan; `Some/None/Ok/Err` magenta | all cyan | cyan is ~70% of variant characters |
| Macro names | std red; user / 3rd-party magenta | all red | std macros outnumber others ~3:1 |
| Attributes | `#` + name red, brackets fg, derive names yellow | whole `#[...]` red | RustRover colours derive names separately anyway |
| Lifetimes | `'static`/`'_` blue1; `'a` orange-tick + red | all blue1 | most lifetime characters |
| `use` `mod` `async` `await` | red | orange | single keyword key |
| `true` / `false` | magenta | orange | RustRover treats booleans as keywords |

To flip any of these, change the entry in `build.py` (e.g. `'ENUM_VARIANT': Constant`) and run
`python3 build.py`, or edit it in Settings → Editor → Color Scheme → Rust.

## C and C++ (CLion)

Same method as Rust: a C++20 sample covering every CLion C/C++ colour key was rendered in Neovim
(nordic + nvim-treesitter + clangd semantic tokens) and the resolved colour of each token recorded.
CLion's own classes were read for the key list: CLion Nova maps every "ReSharper C++" highlighting
onto the classic `OC.*` keys, so the one table covers both the Nova and Classic engines. All 56
keys are set, including the Objective-C ones.

| CLion key(s) | Colour | nordic source |
|---|---|---|
| functions, methods, calls | `#88C0D0` blue2 | Function |
| class, struct, enum, union, typedef / `using`, concept | `#EBCB8B` yellow | Type |
| template parameters (type and non-type), deduction guide | `#EBCB8B` yellow | `@lsp.type.typeParameter` / `class` |
| `int` `void` `bool` `auto` | `#EBCB8B` yellow | `@type.builtin` |
| keywords incl. control flow | `#D08770` orange | Keyword |
| namespace | `#E7C173` yellow.dim | `@lsp.type.namespace` |
| field, enumerator | `#8FBCBB` cyan | `@lsp.type.property` / `enumMember` |
| macro name, constant, number | `#BE9DB8` magenta | `@lsp.type.macro` / `@constant` |
| `#include` `#define` `#if`, global variables | `#BF616A` red | `@keyword.directive` / `globalScope` → Macro |
| `this` | `#5E81AC` blue0 | `@variable.builtin` |
| parameters | fg, *italic* | `@lsp.type.parameter` |
| locals, macro parameters, operators (incl. overloaded), brackets | `#C0C8D8` fg | Variable / Operator |
| string, char, header path, `%d` format tokens | `#A3BE8C` green | String |
| escapes | `#BE9DB8` magenta | `@string.escape` |
| `,` `;` `.` | `#60728A` gray5, *italic* | Delimiter |
| comments incl. Doxygen and its tags | `#4C566A` gray4, *italic* | Comment |
| inactive `#if` branches | gray4, *italic* | `@lsp.type.comment` |

Known differences, where CLion has one key and Neovim two colours:

| What | Neovim | CLion | Why this choice |
|---|---|---|---|
| Global variables | external linkage red; `static` / anonymous-namespace fg | all red | what clangd reports for a plain global |
| Constants | `ALL_CAPS` magenta; lower-case `const` fg | all magenta | matches Rust constants |
| `throw` | red | orange | shares a key with `return` / `break` / `continue` |
| `true` `false` `nullptr` | magenta | orange | CLion treats them as keywords |
| Dependent names (`T::zero()`, `T::value_type`) | blue / yellow | fg | one key for both |

CMake files are covered too (commands blue, `if`/`foreach` orange, argument keywords magenta,
predefined `CMAKE_*` variables blue0). Those were mapped by nordic role, not measured in Neovim.

To change any of these, edit the `CPP` / `CMAKE` tables in `build.py`, or
Settings → Editor → Color Scheme → C/C++.

## Optional: match a default Neovim setup even more closely

Neovim shows no cursor line, usage highlighting or inlay hints by default. In RustRover:
- Editor → General → Appearance → untick **Highlight current line**
- Editor → General → untick **Highlight usages of element at caret**
- Editor → Inlay Hints → Rust → turn off type hints

## Building

```bash
python3 tools/derive_ui_theme.py   # regenerates the UI theme (reads RustRover.app's Islands Darcula)
python3 build.py                   # writes resources/ and dist/*.jar
```

## Credits

- Palette and highlight roles from [nordic.nvim](https://github.com/AlexvZyl/nordic.nvim)
  by Alexander van Zyl (MIT).
- The UI theme is derived from the *Islands Darcula* theme in the
  [IntelliJ Platform](https://github.com/JetBrains/intellij-community) (Apache-2.0),
  with its colours replaced.

MIT licensed: see [LICENSE](LICENSE) and [NOTICE](NOTICE).

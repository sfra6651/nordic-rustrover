# Nordic for RustRover

A RustRover port of [nordic.nvim](https://github.com/AlexvZyl/nordic.nvim) (default options:
`reduced_blue`, italic comments, no bold keywords), built so that **Rust looks the way it does
in Neovim** with treesitter + rust-analyzer.

- **Nordic** editor color scheme
- **Nordic** Islands UI theme: JetBrains' *Islands Darcula* layout recoloured with the nordic
  palette (optional; the editor scheme works with any UI theme)

## Install

1. Download `nordic-rustrover-1.0.0.jar` from the [latest release](https://github.com/sfra6651/nordic-rustrover/releases/latest).
2. Settings → Plugins → ⚙ → **Install Plugin from Disk…** → select the jar, then restart.
3. Settings → Editor → Color Scheme → **Nordic**
   (or Appearance → Theme → **Nordic** for the UI theme too; it selects the scheme for you).

Requires RustRover 2025.3+ (built and checked against 2026.2.4).

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

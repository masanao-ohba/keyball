/*
Copyright 2022 @Yowkees
Copyright 2022 MURAOKA Taro (aka KoRoN, @kaoriya)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

#include QMK_KEYBOARD_H

#include "quantum.h"

// clang-format off
const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
  // Layer 0: Base (QWERTY)
  [0] = LAYOUT_universal(
    LT(3,KC_ESC),      KC_Q,      KC_W,      KC_E,      KC_R,      KC_T,       KC_Y,      KC_U,      KC_I,      KC_O,      KC_P,   KC_BSPC,
    LCTL_T(KC_TAB),      KC_A,      KC_S,      KC_D,      KC_F,      KC_G,       KC_H,      KC_J,      KC_K,      KC_L,   KC_QUOT, LT(3,KC_MINS),
      KC_LSFT,      KC_Z,      KC_X,      KC_C,      KC_V,      KC_B,       KC_N,      KC_M, MT(MOD_LCTL|MOD_RCTL,KC_COMM),    KC_DOT,   KC_SLSH, MT(MOD_LSFT|MOD_RSFT,KC_LBRC),
            _______, LT(2,KC_LNG2), MT(MOD_LGUI,KC_SPC), MT(MOD_LALT,KC_ENT),   KC_CAPS,  MT(MOD_LALT|MOD_RALT,KC_ENT), MT(MOD_LGUI|MOD_RGUI,KC_SPC), MT(MOD_LCTL|MOD_RCTL,KC_LNG2),   KC_RALT,   KC_INT3
  ),

  // Layer 1: Auto Mouse Layer
  [1] = LAYOUT_universal(
       KC_ESC,     KC_NO,     KC_NO,     KC_NO,     KC_NO,     KC_NO,      KC_NO,     KC_NO,     KC_NO,     KC_NO,     KC_NO,     KC_NO,
    LCTL_T(KC_TAB),     KC_NO,     KC_NO,     KC_NO,     KC_NO,     KC_NO,      KC_NO,   KC_BTN1,  C(KC_UP),   KC_BTN2,   SCRL_MO,    KC_TAB,
      KC_LSFT,     KC_NO,     KC_NO,     KC_NO,     KC_NO,     KC_NO,    _______, C(KC_LEFT), C(KC_DOWN), C(KC_RGHT),   _______,   _______,
            _______,   KC_LALT, MT(MOD_LGUI,KC_SPC), MT(MOD_LSFT,KC_ENT),   _______,  MT(MOD_LSFT|MOD_RSFT,KC_ENT), MT(MOD_LCTL|MOD_RCTL,KC_SPC),   _______,   _______,   _______
  ),

  // Layer 2: Numbers + Arrows
  [2] = LAYOUT_universal(
        TO(0),     KC_P1,     KC_P2,     KC_P3,     KC_P4,     KC_P5,      KC_P6,     KC_P7,     KC_P8,     KC_P9,     KC_P0,   KC_BSPC,
      _______,   _______,   _______,   _______,   _______,   _______,    KC_LEFT,   KC_DOWN,     KC_UP,   KC_RGHT,   _______,   _______,
      _______,   _______,   _______,   _______,   _______,   _______,    _______,   _______,   KC_COMM,    KC_DOT,   _______,   _______,
            _______,   _______, MT(MOD_LGUI,KC_SPC), MT(MOD_LALT,KC_ENT),   _______,  MT(MOD_LALT|MOD_RALT,KC_ENT), MT(MOD_LGUI|MOD_RGUI,KC_SPC),   _______,   _______,   _______
  ),

  // Layer 3: Symbols
  [3] = LAYOUT_universal(
      _______,   S(KC_1),   S(KC_2),   S(KC_3),   S(KC_4),   S(KC_5),    S(KC_6),   S(KC_7),   S(KC_8),   S(KC_9),   KC_MINS,    KC_EQL,
      _______,     KC_NO,     KC_NO,     KC_NO,     KC_NO,     KC_NO,      KC_NO,     KC_NO, S(KC_RBRC), S(KC_NUHS),   KC_SCLN,   KC_QUOT,
      _______,     KC_NO,     KC_NO,     KC_NO,     KC_NO,     KC_NO,      KC_NO,     KC_NO,   KC_RBRC,   KC_NUHS,   KC_SLSH, S(KC_INT3),
            _______,   _______,   _______,   _______,   _______,    _______,   _______,   _______, S(KC_INT1), S(KC_INT1)
  ),
};
// clang-format on

// --- Issue 1 Fix: Keep Auto Mouse Layer active while Ctrl is held ---
// When Ctrl+Tab is used on Layer 1 for browser tab switching, the auto mouse
// timeout would normally deactivate the layer between Tab presses. This fix
// forces the auto mouse layer to stay active as long as Ctrl is held.
static bool mouse_layer_force = false;

void matrix_scan_user(void) {
    uint8_t auto_mouse_layer = get_auto_mouse_layer();
    if (get_mods() & MOD_MASK_CTRL) {
        if (IS_LAYER_ON(auto_mouse_layer) && !mouse_layer_force) {
            mouse_layer_force = true;
        }
        if (mouse_layer_force) {
            layer_on(auto_mouse_layer);
        }
    } else {
        mouse_layer_force = false;
    }
}

void keyboard_post_init_user(void) {
    keyball_set_scrollsnap_mode(KEYBALL_SCROLLSNAP_MODE_FREE);
    set_auto_mouse_enable(true);
}

layer_state_t layer_state_set_user(layer_state_t state) {
    // Auto enable scroll mode when the highest layer is 3
    keyball_set_scroll_mode(get_highest_layer(state) == 3);
    return state;
}

#ifdef POINTING_DEVICE_AUTO_MOUSE_ENABLE
// Treat these keycodes as mouse keys so they don't deactivate the Auto Mouse Layer.
// This allows Ctrl+Tab (tab switching) to work on Layer 1 while keeping the layer active.
bool is_mouse_record_user(uint16_t keycode, keyrecord_t* record) {
    switch (keycode) {
        case KC_TAB:
            return true;
        default:
            // Mod-tap keys (e.g. RCTL_T(KC_SPC)) and plain modifiers
            // should not deactivate the auto mouse layer.
            if (IS_QK_MOD_TAP(keycode) ||
                (keycode >= KC_LCTL && keycode <= KC_RGUI)) {
                return true;
            }
            return false;
    }
}
#endif

#ifdef OLED_ENABLE

#    include "lib/oledkit/oledkit.h"

void oledkit_render_info_user(void) {
    keyball_oled_render_keyinfo();
    keyball_oled_render_ballinfo();
    keyball_oled_render_layerinfo();
}
#endif

var _createClass = function() {
    function defineProperties(target, props) {
        for (var i = 0; i < props.length; i++) {
            var descriptor = props[i];
            descriptor.enumerable = descriptor.enumerable || !1, descriptor.configurable = !0, 
            "value" in descriptor && (descriptor.writable = !0), Object.defineProperty(target, descriptor.key, descriptor);
        }
    }
    return function(Constructor, protoProps, staticProps) {
        return protoProps && defineProperties(Constructor.prototype, protoProps), staticProps && defineProperties(Constructor, staticProps), 
        Constructor;
    };
}();

function _classCallCheck(instance, Constructor) {
    if (!(instance instanceof Constructor)) throw new TypeError("Cannot call a class as a function");
}

!function(a, b, c, d) {
    "use strict";
    function k(a, b, c) {
        return setTimeout(q(a, c), b);
    }
    function l(a, b, c) {
        return !!Array.isArray(a) && (m(a, c[b], c), !0);
    }
    function m(a, b, c) {
        var e;
        if (a) if (a.forEach) a.forEach(b, c); else if (a.length !== d) for (e = 0; e < a.length; ) b.call(c, a[e], e, a), 
        e++; else for (e in a) a.hasOwnProperty(e) && b.call(c, a[e], e, a);
    }
    function n(a, b, c) {
        for (var e = Object.keys(b), f = 0; f < e.length; ) (!c || c && a[e[f]] === d) && (a[e[f]] = b[e[f]]), 
        f++;
        return a;
    }
    function o(a, b) {
        return n(a, b, !0);
    }
    function p(a, b, c) {
        var e, d = b.prototype;
        (e = a.prototype = Object.create(d)).constructor = a, e._super = d, c && n(e, c);
    }
    function q(a, b) {
        return function() {
            return a.apply(b, arguments);
        };
    }
    function r(a, b) {
        return typeof a == g ? a.apply(b && b[0] || d, b) : a;
    }
    function s(a, b) {
        return a === d ? b : a;
    }
    function t(a, b, c) {
        m(x(b), function(b) {
            a.addEventListener(b, c, !1);
        });
    }
    function u(a, b, c) {
        m(x(b), function(b) {
            a.removeEventListener(b, c, !1);
        });
    }
    function v(a, b) {
        for (;a; ) {
            if (a == b) return !0;
            a = a.parentNode;
        }
        return !1;
    }
    function w(a, b) {
        return -1 < a.indexOf(b);
    }
    function x(a) {
        return a.trim().split(/\s+/g);
    }
    function y(a, b, c) {
        if (a.indexOf && !c) return a.indexOf(b);
        for (var d = 0; d < a.length; ) {
            if (c && a[d][c] == b || !c && a[d] === b) return d;
            d++;
        }
        return -1;
    }
    function z(a) {
        return Array.prototype.slice.call(a, 0);
    }
    function A(a, b, c) {
        for (var d = [], e = [], f = 0; f < a.length; ) {
            var g = b ? a[f][b] : a[f];
            y(e, g) < 0 && d.push(a[f]), e[f] = g, f++;
        }
        return c && (d = b ? d.sort(function(a, c) {
            return a[b] > c[b];
        }) : d.sort()), d;
    }
    function B(a, b) {
        for (var c, f, g = b[0].toUpperCase() + b.slice(1), h = 0; h < e.length; ) {
            if ((f = (c = e[h]) ? c + g : b) in a) return f;
            h++;
        }
        return d;
    }
    function E(a) {
        var b = a.ownerDocument;
        return b.defaultView || b.parentWindow;
    }
    function ab(a, b) {
        var c = this;
        this.manager = a, this.callback = b, this.element = a.element, this.target = a.options.inputTarget, 
        this.domHandler = function(b) {
            r(a.options.enable, [ a ]) && c.handler(b);
        }, this.init();
    }
    function cb(a, b, c) {
        var d = c.pointers.length, e = c.changedPointers.length, f = b & O && 0 == d - e, g = b & (Q | R) && 0 == d - e;
        c.isFirst = !!f, c.isFinal = !!g, f && (a.session = {}), c.eventType = b, function(a, b) {
            var c = a.session, d = b.pointers, e = d.length;
            c.firstInput || (c.firstInput = gb(b)), 1 < e && !c.firstMultiple ? c.firstMultiple = gb(b) : 1 === e && (c.firstMultiple = !1);
            var f = c.firstInput, g = c.firstMultiple, h = g ? g.center : f.center, i = b.center = hb(d);
            b.timeStamp = j(), b.deltaTime = b.timeStamp - f.timeStamp, b.angle = lb(h, i), 
            b.distance = kb(h, i), function(a, b) {
                var c = b.center, d = a.offsetDelta || {}, e = a.prevDelta || {}, f = a.prevInput || {};
                (b.eventType === O || f.eventType === Q) && (e = a.prevDelta = {
                    x: f.deltaX || 0,
                    y: f.deltaY || 0
                }, d = a.offsetDelta = {
                    x: c.x,
                    y: c.y
                }), b.deltaX = e.x + (c.x - d.x), b.deltaY = e.y + (c.y - d.y);
            }(c, b), b.offsetDirection = jb(b.deltaX, b.deltaY), b.scale = g ? function(a, b) {
                return kb(b[0], b[1], _) / kb(a[0], a[1], _);
            }(g.pointers, d) : 1, b.rotation = g ? function(a, b) {
                return lb(b[1], b[0], _) - lb(a[1], a[0], _);
            }(g.pointers, d) : 0, fb(c, b);
            var k = a.element;
            v(b.srcEvent.target, k) && (k = b.srcEvent.target), b.target = k;
        }(a, c), a.emit("hammer.input", c), a.recognize(c), a.session.prevInput = c;
    }
    function fb(a, b) {
        var f, g, h, j, c = a.lastInterval || b, e = b.timeStamp - c.timeStamp;
        if (b.eventType != R && (N < e || c.velocity === d)) {
            var k = c.deltaX - b.deltaX, l = c.deltaY - b.deltaY, m = function(a, b, c) {
                return {
                    x: b / a || 0,
                    y: c / a || 0
                };
            }(e, k, l);
            g = m.x, h = m.y, f = i(m.x) > i(m.y) ? m.x : m.y, j = jb(k, l), a.lastInterval = b;
        } else f = c.velocity, g = c.velocityX, h = c.velocityY, j = c.direction;
        b.velocity = f, b.velocityX = g, b.velocityY = h, b.direction = j;
    }
    function gb(a) {
        for (var b = [], c = 0; c < a.pointers.length; ) b[c] = {
            clientX: h(a.pointers[c].clientX),
            clientY: h(a.pointers[c].clientY)
        }, c++;
        return {
            timeStamp: j(),
            pointers: b,
            center: hb(b),
            deltaX: a.deltaX,
            deltaY: a.deltaY
        };
    }
    function hb(a) {
        var b = a.length;
        if (1 === b) return {
            x: h(a[0].clientX),
            y: h(a[0].clientY)
        };
        for (var c = 0, d = 0, e = 0; e < b; ) c += a[e].clientX, d += a[e].clientY, e++;
        return {
            x: h(c / b),
            y: h(d / b)
        };
    }
    function jb(a, b) {
        return a === b ? S : i(a) >= i(b) ? 0 < a ? T : U : 0 < b ? V : W;
    }
    function kb(a, b, c) {
        c || (c = $);
        var d = b[c[0]] - a[c[0]], e = b[c[1]] - a[c[1]];
        return Math.sqrt(d * d + e * e);
    }
    function lb(a, b, c) {
        c || (c = $);
        var d = b[c[0]] - a[c[0]], e = b[c[1]] - a[c[1]];
        return 180 * Math.atan2(e, d) / Math.PI;
    }
    function rb() {
        this.evEl = pb, this.evWin = qb, this.allow = !0, this.pressed = !1, ab.apply(this, arguments);
    }
    function wb() {
        this.evEl = ub, this.evWin = vb, ab.apply(this, arguments), this.store = this.manager.session.pointerEvents = [];
    }
    function Ab() {
        this.evTarget = "touchstart", this.evWin = "touchstart touchmove touchend touchcancel", 
        this.started = !1, ab.apply(this, arguments);
    }
    function Eb() {
        this.evTarget = Db, this.targetIds = {}, ab.apply(this, arguments);
    }
    function Gb() {
        ab.apply(this, arguments);
        var a = q(this.handler, this);
        this.touch = new Eb(this.manager, a), this.mouse = new rb(this.manager, a);
    }
    function Pb(a, b) {
        this.manager = a, this.set(b);
    }
    function Yb(a) {
        this.id = C++, this.manager = null, this.options = o(a || {}, this.defaults), this.options.enable = s(this.options.enable, !0), 
        this.state = Rb, this.simultaneous = {}, this.requireFail = [];
    }
    function $b(a) {
        return a == W ? "down" : a == V ? "up" : a == T ? "left" : a == U ? "right" : "";
    }
    function _b(a, b) {
        var c = b.manager;
        return c ? c.get(a) : a;
    }
    function ac() {
        Yb.apply(this, arguments);
    }
    function bc() {
        ac.apply(this, arguments), this.pX = null, this.pY = null;
    }
    function cc() {
        ac.apply(this, arguments);
    }
    function dc() {
        Yb.apply(this, arguments), this._timer = null, this._input = null;
    }
    function ec() {
        ac.apply(this, arguments);
    }
    function fc() {
        ac.apply(this, arguments);
    }
    function gc() {
        Yb.apply(this, arguments), this.pTime = !1, this.pCenter = !1, this._timer = null, 
        this._input = null, this.count = 0;
    }
    function hc(a, b) {
        return (b = b || {}).recognizers = s(b.recognizers, hc.defaults.preset), new kc(a, b);
    }
    function kc(a, b) {
        b = b || {}, this.options = o(b, hc.defaults), this.options.inputTarget = this.options.inputTarget || a, 
        this.handlers = {}, this.session = {}, this.recognizers = [], this.element = a, 
        this.input = function(a) {
            var c = a.options.inputClass;
            return new (c || (H ? wb : I ? Eb : G ? Gb : rb))(a, cb);
        }(this), this.touchAction = new Pb(this, this.options.touchAction), lc(this, !0), 
        m(b.recognizers, function(a) {
            var b = this.add(new a[0](a[1]));
            a[2] && b.recognizeWith(a[2]), a[3] && b.requireFailure(a[3]);
        }, this);
    }
    function lc(a, b) {
        var c = a.element;
        m(a.options.cssProps, function(a, d) {
            c.style[B(c.style, d)] = b ? a : "";
        });
    }
    function mc(a, c) {
        var d = b.createEvent("Event");
        d.initEvent(a, !0, !0), (d.gesture = c).target.dispatchEvent(d);
    }
    var e = [ "", "webkit", "moz", "MS", "ms", "o" ], f = b.createElement("div"), g = "function", h = Math.round, i = Math.abs, j = Date.now, C = 1, G = "ontouchstart" in a, H = B(a, "PointerEvent") !== d, I = G && /mobile|tablet|ip(ad|hone|od)|android/i.test(navigator.userAgent), J = "touch", L = "mouse", N = 25, O = 1, Q = 4, R = 8, S = 1, T = 2, U = 4, V = 8, W = 16, X = T | U, Y = V | W, Z = X | Y, $ = [ "x", "y" ], _ = [ "clientX", "clientY" ];
    ab.prototype = {
        handler: function() {},
        init: function() {
            this.evEl && t(this.element, this.evEl, this.domHandler), this.evTarget && t(this.target, this.evTarget, this.domHandler), 
            this.evWin && t(E(this.element), this.evWin, this.domHandler);
        },
        destroy: function() {
            this.evEl && u(this.element, this.evEl, this.domHandler), this.evTarget && u(this.target, this.evTarget, this.domHandler), 
            this.evWin && u(E(this.element), this.evWin, this.domHandler);
        }
    };
    var ob = {
        mousedown: O,
        mousemove: 2,
        mouseup: Q
    }, pb = "mousedown", qb = "mousemove mouseup";
    p(rb, ab, {
        handler: function(a) {
            var b = ob[a.type];
            b & O && 0 === a.button && (this.pressed = !0), 2 & b && 1 !== a.which && (b = Q), 
            this.pressed && this.allow && (b & Q && (this.pressed = !1), this.callback(this.manager, b, {
                pointers: [ a ],
                changedPointers: [ a ],
                pointerType: L,
                srcEvent: a
            }));
        }
    });
    var sb = {
        pointerdown: O,
        pointermove: 2,
        pointerup: Q,
        pointercancel: R,
        pointerout: R
    }, tb = {
        2: J,
        3: "pen",
        4: L,
        5: "kinect"
    }, ub = "pointerdown", vb = "pointermove pointerup pointercancel";
    a.MSPointerEvent && (ub = "MSPointerDown", vb = "MSPointerMove MSPointerUp MSPointerCancel"), 
    p(wb, ab, {
        handler: function(a) {
            var b = this.store, c = !1, d = a.type.toLowerCase().replace("ms", ""), e = sb[d], f = tb[a.pointerType] || a.pointerType, g = f == J, h = y(b, a.pointerId, "pointerId");
            e & O && (0 === a.button || g) ? h < 0 && (b.push(a), h = b.length - 1) : e & (Q | R) && (c = !0), 
            h < 0 || (b[h] = a, this.callback(this.manager, e, {
                pointers: b,
                changedPointers: [ a ],
                pointerType: f,
                srcEvent: a
            }), c && b.splice(h, 1));
        }
    });
    var xb = {
        touchstart: O,
        touchmove: 2,
        touchend: Q,
        touchcancel: R
    };
    p(Ab, ab, {
        handler: function(a) {
            var b = xb[a.type];
            if (b === O && (this.started = !0), this.started) {
                var c = function(a, b) {
                    var c = z(a.touches), d = z(a.changedTouches);
                    return b & (Q | R) && (c = A(c.concat(d), "identifier", !0)), [ c, d ];
                }.call(this, a, b);
                b & (Q | R) && 0 == c[0].length - c[1].length && (this.started = !1), this.callback(this.manager, b, {
                    pointers: c[0],
                    changedPointers: c[1],
                    pointerType: J,
                    srcEvent: a
                });
            }
        }
    });
    var Cb = {
        touchstart: O,
        touchmove: 2,
        touchend: Q,
        touchcancel: R
    }, Db = "touchstart touchmove touchend touchcancel";
    p(Eb, ab, {
        handler: function(a) {
            var b = Cb[a.type], c = function(a, b) {
                var c = z(a.touches), d = this.targetIds;
                if (b & (2 | O) && 1 === c.length) return d[c[0].identifier] = !0, [ c, c ];
                var e, f, g = z(a.changedTouches), h = [], i = this.target;
                if (f = c.filter(function(a) {
                    return v(a.target, i);
                }), b === O) for (e = 0; e < f.length; ) d[f[e].identifier] = !0, e++;
                for (e = 0; e < g.length; ) d[g[e].identifier] && h.push(g[e]), b & (Q | R) && delete d[g[e].identifier], 
                e++;
                return h.length ? [ A(f.concat(h), "identifier", !0), h ] : void 0;
            }.call(this, a, b);
            c && this.callback(this.manager, b, {
                pointers: c[0],
                changedPointers: c[1],
                pointerType: J,
                srcEvent: a
            });
        }
    }), p(Gb, ab, {
        handler: function(a, b, c) {
            var d = c.pointerType == J, e = c.pointerType == L;
            if (d) this.mouse.allow = !1; else if (e && !this.mouse.allow) return;
            b & (Q | R) && (this.mouse.allow = !0), this.callback(a, b, c);
        },
        destroy: function() {
            this.touch.destroy(), this.mouse.destroy();
        }
    });
    var Hb = B(f.style, "touchAction"), Ib = Hb !== d, Jb = "compute", Lb = "manipulation", Mb = "none", Nb = "pan-x", Ob = "pan-y";
    Pb.prototype = {
        set: function(a) {
            a == Jb && (a = this.compute()), Ib && (this.manager.element.style[Hb] = a), this.actions = a.toLowerCase().trim();
        },
        update: function() {
            this.set(this.manager.options.touchAction);
        },
        compute: function() {
            var a = [];
            return m(this.manager.recognizers, function(b) {
                r(b.options.enable, [ b ]) && (a = a.concat(b.getTouchAction()));
            }), function(a) {
                if (w(a, Mb)) return Mb;
                var b = w(a, Nb), c = w(a, Ob);
                return b && c ? Nb + " " + Ob : b || c ? b ? Nb : Ob : w(a, Lb) ? Lb : "auto";
            }(a.join(" "));
        },
        preventDefaults: function(a) {
            if (!Ib) {
                var b = a.srcEvent, c = a.offsetDirection;
                if (this.manager.session.prevented) return void b.preventDefault();
                var d = this.actions, e = w(d, Mb), f = w(d, Ob), g = w(d, Nb);
                return e || f && c & X || g && c & Y ? this.preventSrc(b) : void 0;
            }
        },
        preventSrc: function(a) {
            this.manager.session.prevented = !0, a.preventDefault();
        }
    };
    var Rb = 1, Sb = 2, Tb = 4, Ub = 8, Vb = Ub, Wb = 16;
    Yb.prototype = {
        defaults: {},
        set: function(a) {
            return n(this.options, a), this.manager && this.manager.touchAction.update(), this;
        },
        recognizeWith: function(a) {
            if (l(a, "recognizeWith", this)) return this;
            var b = this.simultaneous;
            return b[(a = _b(a, this)).id] || (b[a.id] = a).recognizeWith(this), this;
        },
        dropRecognizeWith: function(a) {
            return l(a, "dropRecognizeWith", this) || (a = _b(a, this), delete this.simultaneous[a.id]), 
            this;
        },
        requireFailure: function(a) {
            if (l(a, "requireFailure", this)) return this;
            var b = this.requireFail;
            return -1 === y(b, a = _b(a, this)) && (b.push(a), a.requireFailure(this)), this;
        },
        dropRequireFailure: function(a) {
            if (l(a, "dropRequireFailure", this)) return this;
            a = _b(a, this);
            var b = y(this.requireFail, a);
            return -1 < b && this.requireFail.splice(b, 1), this;
        },
        hasRequireFailures: function() {
            return 0 < this.requireFail.length;
        },
        canRecognizeWith: function(a) {
            return !!this.simultaneous[a.id];
        },
        emit: function(a) {
            function d(d) {
                b.manager.emit(b.options.event + (d ? function(a) {
                    return a & Wb ? "cancel" : a & Ub ? "end" : a & Tb ? "move" : a & Sb ? "start" : "";
                }(c) : ""), a);
            }
            var b = this, c = this.state;
            c < Ub && d(!0), d(), Ub <= c && d(!0);
        },
        tryEmit: function(a) {
            return this.canEmit() ? this.emit(a) : void (this.state = 32);
        },
        canEmit: function() {
            for (var a = 0; a < this.requireFail.length; ) {
                if (!(this.requireFail[a].state & (32 | Rb))) return !1;
                a++;
            }
            return !0;
        },
        recognize: function(a) {
            var b = n({}, a);
            return r(this.options.enable, [ this, b ]) ? (this.state & (Vb | Wb | 32) && (this.state = Rb), 
            this.state = this.process(b), void (this.state & (Sb | Tb | Ub | Wb) && this.tryEmit(b))) : (this.reset(), 
            void (this.state = 32));
        },
        process: function() {},
        getTouchAction: function() {},
        reset: function() {}
    }, p(ac, Yb, {
        defaults: {
            pointers: 1
        },
        attrTest: function(a) {
            var b = this.options.pointers;
            return 0 === b || a.pointers.length === b;
        },
        process: function(a) {
            var b = this.state, c = a.eventType, d = b & (Sb | Tb), e = this.attrTest(a);
            return d && (c & R || !e) ? b | Wb : d || e ? c & Q ? b | Ub : b & Sb ? b | Tb : Sb : 32;
        }
    }), p(bc, ac, {
        defaults: {
            event: "pan",
            threshold: 10,
            pointers: 1,
            direction: Z
        },
        getTouchAction: function() {
            var a = this.options.direction, b = [];
            return a & X && b.push(Ob), a & Y && b.push(Nb), b;
        },
        directionTest: function(a) {
            var b = this.options, c = !0, d = a.distance, e = a.direction, f = a.deltaX, g = a.deltaY;
            return e & b.direction || (d = b.direction & X ? (e = 0 === f ? S : f < 0 ? T : U, 
            c = f != this.pX, Math.abs(a.deltaX)) : (e = 0 === g ? S : g < 0 ? V : W, c = g != this.pY, 
            Math.abs(a.deltaY))), a.direction = e, c && d > b.threshold && e & b.direction;
        },
        attrTest: function(a) {
            return ac.prototype.attrTest.call(this, a) && (this.state & Sb || !(this.state & Sb) && this.directionTest(a));
        },
        emit: function(a) {
            this.pX = a.deltaX, this.pY = a.deltaY;
            var b = $b(a.direction);
            b && this.manager.emit(this.options.event + b, a), this._super.emit.call(this, a);
        }
    }), p(cc, ac, {
        defaults: {
            event: "pinch",
            threshold: 0,
            pointers: 2
        },
        getTouchAction: function() {
            return [ Mb ];
        },
        attrTest: function(a) {
            return this._super.attrTest.call(this, a) && (Math.abs(a.scale - 1) > this.options.threshold || this.state & Sb);
        },
        emit: function(a) {
            if (this._super.emit.call(this, a), 1 !== a.scale) {
                var b = a.scale < 1 ? "in" : "out";
                this.manager.emit(this.options.event + b, a);
            }
        }
    }), p(dc, Yb, {
        defaults: {
            event: "press",
            pointers: 1,
            time: 500,
            threshold: 5
        },
        getTouchAction: function() {
            return [ "auto" ];
        },
        process: function(a) {
            var b = this.options, c = a.pointers.length === b.pointers, d = a.distance < b.threshold, e = a.deltaTime > b.time;
            if (this._input = a, !d || !c || a.eventType & (Q | R) && !e) this.reset(); else if (a.eventType & O) this.reset(), 
            this._timer = k(function() {
                this.state = Vb, this.tryEmit();
            }, b.time, this); else if (a.eventType & Q) return Vb;
            return 32;
        },
        reset: function() {
            clearTimeout(this._timer);
        },
        emit: function(a) {
            this.state === Vb && (a && a.eventType & Q ? this.manager.emit(this.options.event + "up", a) : (this._input.timeStamp = j(), 
            this.manager.emit(this.options.event, this._input)));
        }
    }), p(ec, ac, {
        defaults: {
            event: "rotate",
            threshold: 0,
            pointers: 2
        },
        getTouchAction: function() {
            return [ Mb ];
        },
        attrTest: function(a) {
            return this._super.attrTest.call(this, a) && (Math.abs(a.rotation) > this.options.threshold || this.state & Sb);
        }
    }), p(fc, ac, {
        defaults: {
            event: "swipe",
            threshold: 10,
            velocity: .65,
            direction: X | Y,
            pointers: 1
        },
        getTouchAction: function() {
            return bc.prototype.getTouchAction.call(this);
        },
        attrTest: function(a) {
            var c, b = this.options.direction;
            return b & (X | Y) ? c = a.velocity : b & X ? c = a.velocityX : b & Y && (c = a.velocityY), 
            this._super.attrTest.call(this, a) && b & a.direction && a.distance > this.options.threshold && i(c) > this.options.velocity && a.eventType & Q;
        },
        emit: function(a) {
            var b = $b(a.direction);
            b && this.manager.emit(this.options.event + b, a), this.manager.emit(this.options.event, a);
        }
    }), p(gc, Yb, {
        defaults: {
            event: "tap",
            pointers: 1,
            taps: 1,
            interval: 300,
            time: 250,
            threshold: 2,
            posThreshold: 10
        },
        getTouchAction: function() {
            return [ Lb ];
        },
        process: function(a) {
            var b = this.options, c = a.pointers.length === b.pointers, d = a.distance < b.threshold, e = a.deltaTime < b.time;
            if (this.reset(), a.eventType & O && 0 === this.count) return this.failTimeout();
            if (d && e && c) {
                if (a.eventType != Q) return this.failTimeout();
                var f = !this.pTime || a.timeStamp - this.pTime < b.interval, g = !this.pCenter || kb(this.pCenter, a.center) < b.posThreshold;
                if (this.pTime = a.timeStamp, this.pCenter = a.center, g && f ? this.count += 1 : this.count = 1, 
                this._input = a, 0 === this.count % b.taps) return this.hasRequireFailures() ? (this._timer = k(function() {
                    this.state = Vb, this.tryEmit();
                }, b.interval, this), Sb) : Vb;
            }
            return 32;
        },
        failTimeout: function() {
            return this._timer = k(function() {
                this.state = 32;
            }, this.options.interval, this), 32;
        },
        reset: function() {
            clearTimeout(this._timer);
        },
        emit: function() {
            this.state == Vb && (this._input.tapCount = this.count, this.manager.emit(this.options.event, this._input));
        }
    }), hc.VERSION = "2.0.4", hc.defaults = {
        domEvents: !1,
        touchAction: Jb,
        enable: !0,
        inputTarget: null,
        inputClass: null,
        preset: [ [ ec, {
            enable: !1
        } ], [ cc, {
            enable: !1
        }, [ "rotate" ] ], [ fc, {
            direction: X
        } ], [ bc, {
            direction: X
        }, [ "swipe" ] ], [ gc ], [ gc, {
            event: "doubletap",
            taps: 2
        }, [ "tap" ] ], [ dc ] ],
        cssProps: {
            userSelect: "default",
            touchSelect: "none",
            touchCallout: "none",
            contentZooming: "none",
            userDrag: "none",
            tapHighlightColor: "rgba(0,0,0,0)"
        }
    };
    kc.prototype = {
        set: function(a) {
            return n(this.options, a), a.touchAction && this.touchAction.update(), a.inputTarget && (this.input.destroy(), 
            this.input.target = a.inputTarget, this.input.init()), this;
        },
        stop: function(a) {
            this.session.stopped = a ? 2 : 1;
        },
        recognize: function(a) {
            var b = this.session;
            if (!b.stopped) {
                this.touchAction.preventDefaults(a);
                var c, d = this.recognizers, e = b.curRecognizer;
                (!e || e && e.state & Vb) && (e = b.curRecognizer = null);
                for (var f = 0; f < d.length; ) c = d[f], 2 === b.stopped || e && c != e && !c.canRecognizeWith(e) ? c.reset() : c.recognize(a), 
                !e && c.state & (Sb | Tb | Ub) && (e = b.curRecognizer = c), f++;
            }
        },
        get: function(a) {
            if (a instanceof Yb) return a;
            for (var b = this.recognizers, c = 0; c < b.length; c++) if (b[c].options.event == a) return b[c];
            return null;
        },
        add: function(a) {
            if (l(a, "add", this)) return this;
            var b = this.get(a.options.event);
            return b && this.remove(b), this.recognizers.push(a), (a.manager = this).touchAction.update(), 
            a;
        },
        remove: function(a) {
            if (l(a, "remove", this)) return this;
            var b = this.recognizers;
            return a = this.get(a), b.splice(y(b, a), 1), this.touchAction.update(), this;
        },
        on: function(a, b) {
            var c = this.handlers;
            return m(x(a), function(a) {
                c[a] = c[a] || [], c[a].push(b);
            }), this;
        },
        off: function(a, b) {
            var c = this.handlers;
            return m(x(a), function(a) {
                b ? c[a].splice(y(c[a], b), 1) : delete c[a];
            }), this;
        },
        emit: function(a, b) {
            this.options.domEvents && mc(a, b);
            var c = this.handlers[a] && this.handlers[a].slice();
            if (c && c.length) {
                b.type = a, b.preventDefault = function() {
                    b.srcEvent.preventDefault();
                };
                for (var d = 0; d < c.length; ) c[d](b), d++;
            }
        },
        destroy: function() {
            this.element && lc(this, !1), this.handlers = {}, this.session = {}, this.input.destroy(), 
            this.element = null;
        }
    }, n(hc, {
        INPUT_START: O,
        INPUT_MOVE: 2,
        INPUT_END: Q,
        INPUT_CANCEL: R,
        STATE_POSSIBLE: Rb,
        STATE_BEGAN: Sb,
        STATE_CHANGED: Tb,
        STATE_ENDED: Ub,
        STATE_RECOGNIZED: Vb,
        STATE_CANCELLED: Wb,
        STATE_FAILED: 32,
        DIRECTION_NONE: S,
        DIRECTION_LEFT: T,
        DIRECTION_RIGHT: U,
        DIRECTION_UP: V,
        DIRECTION_DOWN: W,
        DIRECTION_HORIZONTAL: X,
        DIRECTION_VERTICAL: Y,
        DIRECTION_ALL: Z,
        Manager: kc,
        Input: ab,
        TouchAction: Pb,
        TouchInput: Eb,
        MouseInput: rb,
        PointerEventInput: wb,
        TouchMouseInput: Gb,
        SingleTouchInput: Ab,
        Recognizer: Yb,
        AttrRecognizer: ac,
        Tap: gc,
        Pan: bc,
        Swipe: fc,
        Pinch: cc,
        Rotate: ec,
        Press: dc,
        on: t,
        off: u,
        each: m,
        merge: o,
        extend: n,
        inherit: p,
        bindFn: q,
        prefixed: B
    }), typeof define == g && define.amd ? define(function() {
        return hc;
    }) : "undefined" != typeof module && module.exports ? module.exports = hc : a.Hammer = hc;
}(window, document), jQuery.Velocity ? console.log("Velocity is already loaded. You may be needlessly importing Velocity again; note that Materialize includes Velocity.") : (function(e) {
    function t(e) {
        var t = e.length, a = r.type(e);
        return "function" !== a && !r.isWindow(e) && (!(1 !== e.nodeType || !t) || ("array" === a || 0 === t || "number" == typeof t && 0 < t && t - 1 in e));
    }
    if (!e.jQuery) {
        var r = function(e, t) {
            return new r.fn.init(e, t);
        };
        r.isWindow = function(e) {
            return null != e && e == e.window;
        }, r.type = function(e) {
            return null == e ? e + "" : "object" == typeof e || "function" == typeof e ? n[i.call(e)] || "object" : typeof e;
        }, r.isArray = Array.isArray || function(e) {
            return "array" === r.type(e);
        }, r.isPlainObject = function(e) {
            var t;
            if (!e || "object" !== r.type(e) || e.nodeType || r.isWindow(e)) return !1;
            try {
                if (e.constructor && !o.call(e, "constructor") && !o.call(e.constructor.prototype, "isPrototypeOf")) return !1;
            } catch (a) {
                return !1;
            }
            for (t in e) ;
            return void 0 === t || o.call(e, t);
        }, r.each = function(e, r, a) {
            var o = 0, i = e.length, s = t(e);
            if (a) {
                if (s) for (;o < i && !1 !== r.apply(e[o], a); o++) ; else for (o in e) if (!1 === r.apply(e[o], a)) break;
            } else if (s) for (;o < i && !1 !== r.call(e[o], o, e[o]); o++) ; else for (o in e) if (!1 === r.call(e[o], o, e[o])) break;
            return e;
        }, r.data = function(e, t, n) {
            if (void 0 === n) {
                var i = (o = e[r.expando]) && a[o];
                if (void 0 === t) return i;
                if (i && t in i) return i[t];
            } else if (void 0 !== t) {
                var o = e[r.expando] || (e[r.expando] = ++r.uuid);
                return a[o] = a[o] || {}, a[o][t] = n;
            }
        }, r.removeData = function(e, t) {
            var n = e[r.expando], o = n && a[n];
            o && r.each(t, function(e, t) {
                delete o[t];
            });
        }, r.extend = function() {
            var e, t, a, n, o, i, s = arguments[0] || {}, l = 1, u = arguments.length, c = !1;
            for ("boolean" == typeof s && (c = s, s = arguments[l] || {}, l++), "object" != typeof s && "function" !== r.type(s) && (s = {}), 
            l === u && (s = this, l--); l < u; l++) if (null != (o = arguments[l])) for (n in o) e = s[n], 
            s !== (a = o[n]) && (c && a && (r.isPlainObject(a) || (t = r.isArray(a))) ? (i = t ? (t = !1, 
            e && r.isArray(e) ? e : []) : e && r.isPlainObject(e) ? e : {}, s[n] = r.extend(c, i, a)) : void 0 !== a && (s[n] = a));
            return s;
        }, r.queue = function(e, a, n) {
            if (e) {
                a = (a || "fx") + "queue";
                var i = r.data(e, a);
                return n ? (!i || r.isArray(n) ? i = r.data(e, a, function(e, r) {
                    var a = r || [];
                    return null != e && (t(Object(e)) ? function(e, t) {
                        for (var r = +t.length, a = 0, n = e.length; a < r; ) e[n++] = t[a++];
                        if (r != r) for (;void 0 !== t[a]; ) e[n++] = t[a++];
                        e.length = n;
                    }(a, "string" == typeof e ? [ e ] : e) : [].push.call(a, e)), a;
                }(n)) : i.push(n), i) : i || [];
            }
        }, r.dequeue = function(e, t) {
            r.each(e.nodeType ? [ e ] : e, function(e, a) {
                t = t || "fx";
                var n = r.queue(a, t), o = n.shift();
                "inprogress" === o && (o = n.shift()), o && ("fx" === t && n.unshift("inprogress"), 
                o.call(a, function() {
                    r.dequeue(a, t);
                }));
            });
        }, r.fn = r.prototype = {
            init: function(e) {
                if (e.nodeType) return this[0] = e, this;
                throw new Error("Not a DOM node.");
            },
            offset: function() {
                var t = this[0].getBoundingClientRect ? this[0].getBoundingClientRect() : {
                    top: 0,
                    left: 0
                };
                return {
                    top: t.top + (e.pageYOffset || document.scrollTop || 0) - (document.clientTop || 0),
                    left: t.left + (e.pageXOffset || document.scrollLeft || 0) - (document.clientLeft || 0)
                };
            },
            position: function() {
                function e() {
                    for (var e = this.offsetParent || document; e && "html" === !e.nodeType.toLowerCase && "static" === e.style.position; ) e = e.offsetParent;
                    return e || document;
                }
                var t = this[0], e = e.apply(t), a = this.offset(), n = /^(?:body|html)$/i.test(e.nodeName) ? {
                    top: 0,
                    left: 0
                } : r(e).offset();
                return a.top -= parseFloat(t.style.marginTop) || 0, a.left -= parseFloat(t.style.marginLeft) || 0, 
                e.style && (n.top += parseFloat(e.style.borderTopWidth) || 0, n.left += parseFloat(e.style.borderLeftWidth) || 0), 
                {
                    top: a.top - n.top,
                    left: a.left - n.left
                };
            }
        };
        var a = {};
        r.expando = "velocity" + new Date().getTime(), r.uuid = 0;
        for (var n = {}, o = n.hasOwnProperty, i = n.toString, s = "Boolean Number String Function Array Date RegExp Object Error".split(" "), l = 0; l < s.length; l++) n["[object " + s[l] + "]"] = s[l].toLowerCase();
        r.fn.init.prototype = r.fn, e.Velocity = {
            Utilities: r
        };
    }
}(window), function(e) {
    "object" == typeof module && "object" == typeof module.exports ? module.exports = e() : "function" == typeof define && define.amd ? define(e) : e();
}(function() {
    return function(e, t, r, a) {
        function o(e) {
            return m.isWrapped(e) ? e = [].slice.call(e) : m.isNode(e) && (e = [ e ]), e;
        }
        function i(e) {
            var t = f.data(e, "velocity");
            return null === t ? a : t;
        }
        function l(e, r, a, n) {
            function o(e, t) {
                return 1 - 3 * t + 3 * e;
            }
            function i(e, t) {
                return 3 * t - 6 * e;
            }
            function s(e) {
                return 3 * e;
            }
            function l(e, t, r) {
                return ((o(t, r) * e + i(t, r)) * e + s(t)) * e;
            }
            function u(e, t, r) {
                return 3 * o(t, r) * e * e + 2 * i(t, r) * e + s(t);
            }
            function c(t, r) {
                for (var n = 0; n < m; ++n) {
                    var o = u(r, e, a);
                    if (0 === o) return r;
                    r -= (l(r, e, a) - t) / o;
                }
                return r;
            }
            function f(t, r, n) {
                for (var o, i, s = 0; 0 < (o = l(i = r + (n - r) / 2, e, a) - t) ? n = i : r = i, 
                Math.abs(o) > h && ++s < v; ) ;
                return i;
            }
            function g() {
                V = !0, (e != r || a != n) && function() {
                    for (var t = 0; t < b; ++t) w[t] = l(t * x, e, a);
                }();
            }
            var m = 4, h = 1e-7, v = 10, b = 11, x = 1 / (b - 1), S = "Float32Array" in t;
            if (4 !== arguments.length) return !1;
            for (var P = 0; P < 4; ++P) if ("number" != typeof arguments[P] || isNaN(arguments[P]) || !isFinite(arguments[P])) return !1;
            e = Math.min(e, 1), a = Math.min(a, 1), e = Math.max(e, 0), a = Math.max(a, 0);
            var w = S ? new Float32Array(b) : new Array(b), V = !1, C = function(t) {
                return V || g(), e === r && a === n ? t : 0 === t ? 0 : 1 === t ? 1 : l(function(t) {
                    for (var r = 0, n = 1, o = b - 1; n != o && w[n] <= t; ++n) r += x;
                    var s = r + (t - w[--n]) / (w[n + 1] - w[n]) * x, l = u(s, e, a);
                    return .001 <= l ? c(t, s) : 0 == l ? s : f(t, r, r + x);
                }(t), r, n);
            };
            C.getControlPoints = function() {
                return [ {
                    x: e,
                    y: r
                }, {
                    x: a,
                    y: n
                } ];
            };
            var T = "generateBezier(" + [ e, r, a, n ] + ")";
            return C.toString = function() {
                return T;
            }, C;
        }
        function u(e, t) {
            var r = e;
            return m.isString(e) ? b.Easings[e] || (r = !1) : r = m.isArray(e) && 1 === e.length ? function(e) {
                return function(t) {
                    return Math.round(t * e) * (1 / e);
                };
            }.apply(null, e) : m.isArray(e) && 2 === e.length ? x.apply(null, e.concat([ t ])) : !(!m.isArray(e) || 4 !== e.length) && l.apply(null, e), 
            !1 === r && (r = b.Easings[b.defaults.easing] ? b.defaults.easing : v), r;
        }
        function c(e) {
            if (e) {
                var t = new Date().getTime(), r = b.State.calls.length;
                1e4 < r && (b.State.calls = function(e) {
                    for (var t = -1, r = e ? e.length : 0, a = []; ++t < r; ) {
                        var n = e[t];
                        n && a.push(n);
                    }
                    return a;
                }(b.State.calls));
                for (var o = 0; o < r; o++) if (b.State.calls[o]) {
                    var s = b.State.calls[o], l = s[0], u = s[2], d = s[3], g = !!d, y = null;
                    d || (d = b.State.calls[o][3] = t - 16);
                    for (var h = Math.min((t - d) / u.duration, 1), v = 0, x = l.length; v < x; v++) {
                        var P = l[v], V = P.element;
                        if (i(V)) {
                            var C = !1;
                            if (u.display !== a && null !== u.display && "none" !== u.display) {
                                if ("flex" === u.display) {
                                    f.each([ "-webkit-box", "-moz-box", "-ms-flexbox", "-webkit-flex" ], function(e, t) {
                                        S.setPropertyValue(V, "display", t);
                                    });
                                }
                                S.setPropertyValue(V, "display", u.display);
                            }
                            for (var k in u.visibility !== a && "hidden" !== u.visibility && S.setPropertyValue(V, "visibility", u.visibility), 
                            P) if ("element" !== k) {
                                var A, F = P[k], j = m.isString(F.easing) ? b.Easings[F.easing] : F.easing;
                                if (1 === h) A = F.endValue; else {
                                    var E = F.endValue - F.startValue;
                                    if (A = F.startValue + E * j(h, u, E), !g && A === F.currentValue) continue;
                                }
                                if (F.currentValue = A, "tween" === k) y = A; else {
                                    if (S.Hooks.registered[k]) {
                                        var H = S.Hooks.getRoot(k), N = i(V).rootPropertyValueCache[H];
                                        N && (F.rootPropertyValue = N);
                                    }
                                    var L = S.setPropertyValue(V, k, F.currentValue + (0 === parseFloat(A) ? "" : F.unitType), F.rootPropertyValue, F.scrollData);
                                    S.Hooks.registered[k] && (i(V).rootPropertyValueCache[H] = S.Normalizations.registered[H] ? S.Normalizations.registered[H]("extract", null, L[1]) : L[1]), 
                                    "transform" === L[0] && (C = !0);
                                }
                            }
                            u.mobileHA && i(V).transformCache.translate3d === a && (i(V).transformCache.translate3d = "(0px, 0px, 0px)", 
                            C = !0), C && S.flushTransformCache(V);
                        }
                    }
                    u.display !== a && "none" !== u.display && (b.State.calls[o][2].display = !1), u.visibility !== a && "hidden" !== u.visibility && (b.State.calls[o][2].visibility = !1), 
                    u.progress && u.progress.call(s[1], s[1], h, Math.max(0, d + u.duration - t), d, y), 
                    1 === h && p(o);
                }
            }
            b.State.isTicking && w(c);
        }
        function p(e, t) {
            if (!b.State.calls[e]) return !1;
            for (var r = b.State.calls[e][0], n = b.State.calls[e][1], o = b.State.calls[e][2], s = b.State.calls[e][4], l = !1, u = 0, c = r.length; u < c; u++) {
                var p = r[u].element;
                if (t || o.loop || ("none" === o.display && S.setPropertyValue(p, "display", o.display), 
                "hidden" === o.visibility && S.setPropertyValue(p, "visibility", o.visibility)), 
                !0 !== o.loop && (f.queue(p)[1] === a || !/\.velocityQueueEntryFlag/i.test(f.queue(p)[1])) && i(p)) {
                    i(p).isAnimating = !1;
                    var d = !(i(p).rootPropertyValueCache = {});
                    f.each(S.Lists.transforms3D, function(e, t) {
                        var r = /^scale/.test(t) ? 1 : 0, n = i(p).transformCache[t];
                        i(p).transformCache[t] !== a && new RegExp("^\\(" + r + "[^.]").test(n) && (d = !0, 
                        delete i(p).transformCache[t]);
                    }), o.mobileHA && (d = !0, delete i(p).transformCache.translate3d), d && S.flushTransformCache(p), 
                    S.Values.removeClass(p, "velocity-animating");
                }
                if (!t && o.complete && !o.loop && u === c - 1) try {
                    o.complete.call(n, n);
                } catch (g) {
                    setTimeout(function() {
                        throw g;
                    }, 1);
                }
                s && !0 !== o.loop && s(n), i(p) && !0 === o.loop && !t && (f.each(i(p).tweensContainer, function(e, t) {
                    /^rotate/.test(e) && 360 === parseFloat(t.endValue) && (t.endValue = 0, t.startValue = 360), 
                    /^backgroundPosition/.test(e) && 100 === parseFloat(t.endValue) && "%" === t.unitType && (t.endValue = 0, 
                    t.startValue = 100);
                }), b(p, "reverse", {
                    loop: !0,
                    delay: o.delay
                })), !1 !== o.queue && f.dequeue(p, o.queue);
            }
            b.State.calls[e] = !1;
            for (var m = 0, y = b.State.calls.length; m < y; m++) if (!1 !== b.State.calls[m]) {
                l = !0;
                break;
            }
            !1 === l && (b.State.isTicking = !1, delete b.State.calls, b.State.calls = []);
        }
        var f, d = function() {
            if (r.documentMode) return r.documentMode;
            for (var e = 7; 4 < e; e--) {
                var t = r.createElement("div");
                if (t.innerHTML = "\x3c!--[if IE " + e + "]><span></span><![endif]--\x3e", t.getElementsByTagName("span").length) return t = null, 
                e;
            }
            return a;
        }(), g = function() {
            var e = 0;
            return t.webkitRequestAnimationFrame || t.mozRequestAnimationFrame || function(t) {
                var r, a = new Date().getTime();
                return r = Math.max(0, 16 - (a - e)), e = a + r, setTimeout(function() {
                    t(a + r);
                }, r);
            };
        }(), m = {
            isString: function(e) {
                return "string" == typeof e;
            },
            isArray: Array.isArray || function(e) {
                return "[object Array]" === Object.prototype.toString.call(e);
            },
            isFunction: function(e) {
                return "[object Function]" === Object.prototype.toString.call(e);
            },
            isNode: function(e) {
                return e && e.nodeType;
            },
            isNodeList: function(e) {
                return "object" == typeof e && /^\[object (HTMLCollection|NodeList|Object)\]$/.test(Object.prototype.toString.call(e)) && e.length !== a && (0 === e.length || "object" == typeof e[0] && 0 < e[0].nodeType);
            },
            isWrapped: function(e) {
                return e && (e.jquery || t.Zepto && t.Zepto.zepto.isZ(e));
            },
            isSVG: function(e) {
                return t.SVGElement && e instanceof t.SVGElement;
            },
            isEmptyObject: function(e) {
                for (var t in e) return !1;
                return !0;
            }
        }, y = !1;
        if (e.fn && e.fn.jquery ? (f = e, y = !0) : f = t.Velocity.Utilities, d <= 8 && !y) throw new Error("Velocity: IE8 and below require jQuery to be loaded before Velocity.");
        if (!(d <= 7)) {
            var v = "swing", b = {
                State: {
                    isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
                    isAndroid: /Android/i.test(navigator.userAgent),
                    isGingerbread: /Android 2\.3\.[3-7]/i.test(navigator.userAgent),
                    isChrome: t.chrome,
                    isFirefox: /Firefox/i.test(navigator.userAgent),
                    prefixElement: r.createElement("div"),
                    prefixMatches: {},
                    scrollAnchor: null,
                    scrollPropertyLeft: null,
                    scrollPropertyTop: null,
                    isTicking: !1,
                    calls: []
                },
                CSS: {},
                Utilities: f,
                Redirects: {},
                Easings: {},
                Promise: t.Promise,
                defaults: {
                    queue: "",
                    duration: 400,
                    easing: v,
                    begin: a,
                    complete: a,
                    progress: a,
                    display: a,
                    visibility: a,
                    loop: !1,
                    delay: !1,
                    mobileHA: !0,
                    _cacheValues: !0
                },
                init: function(e) {
                    f.data(e, "velocity", {
                        isSVG: m.isSVG(e),
                        isAnimating: !1,
                        computedStyle: null,
                        tweensContainer: null,
                        rootPropertyValueCache: {},
                        transformCache: {}
                    });
                },
                hook: null,
                mock: !1,
                version: {
                    major: 1,
                    minor: 2,
                    patch: 2
                },
                debug: !1
            };
            t.pageYOffset !== a ? (b.State.scrollAnchor = t, b.State.scrollPropertyLeft = "pageXOffset", 
            b.State.scrollPropertyTop = "pageYOffset") : (b.State.scrollAnchor = r.documentElement || r.body.parentNode || r.body, 
            b.State.scrollPropertyLeft = "scrollLeft", b.State.scrollPropertyTop = "scrollTop");
            var x = function() {
                function e(e) {
                    return -e.tension * e.x - e.friction * e.v;
                }
                function t(t, r, a) {
                    var n = {
                        x: t.x + a.dx * r,
                        v: t.v + a.dv * r,
                        tension: t.tension,
                        friction: t.friction
                    };
                    return {
                        dx: n.v,
                        dv: e(n)
                    };
                }
                function r(r, a) {
                    var n = {
                        dx: r.v,
                        dv: e(r)
                    }, o = t(r, .5 * a, n), i = t(r, .5 * a, o), s = t(r, a, i), l = 1 / 6 * (n.dx + 2 * (o.dx + i.dx) + s.dx), u = 1 / 6 * (n.dv + 2 * (o.dv + i.dv) + s.dv);
                    return r.x = r.x + l * a, r.v = r.v + u * a, r;
                }
                return function a(e, t, n) {
                    var o, i, s, l = {
                        x: -1,
                        v: 0,
                        tension: null,
                        friction: null
                    }, u = [ 0 ], c = 0;
                    for (e = parseFloat(e) || 500, t = parseFloat(t) || 20, n = n || null, l.tension = e, 
                    l.friction = t, i = (o = null !== n) ? (c = a(e, t)) / n * .016 : .016; s = r(s || l, i), 
                    u.push(1 + s.x), c += 16, 1e-4 < Math.abs(s.x) && 1e-4 < Math.abs(s.v); ) ;
                    return o ? function(e) {
                        return u[e * (u.length - 1) | 0];
                    } : c;
                };
            }();
            b.Easings = {
                linear: function(e) {
                    return e;
                },
                swing: function(e) {
                    return .5 - Math.cos(e * Math.PI) / 2;
                },
                spring: function(e) {
                    return 1 - Math.cos(4.5 * e * Math.PI) * Math.exp(6 * -e);
                }
            }, f.each([ [ "ease", [ .25, .1, .25, 1 ] ], [ "ease-in", [ .42, 0, 1, 1 ] ], [ "ease-out", [ 0, 0, .58, 1 ] ], [ "ease-in-out", [ .42, 0, .58, 1 ] ], [ "easeInSine", [ .47, 0, .745, .715 ] ], [ "easeOutSine", [ .39, .575, .565, 1 ] ], [ "easeInOutSine", [ .445, .05, .55, .95 ] ], [ "easeInQuad", [ .55, .085, .68, .53 ] ], [ "easeOutQuad", [ .25, .46, .45, .94 ] ], [ "easeInOutQuad", [ .455, .03, .515, .955 ] ], [ "easeInCubic", [ .55, .055, .675, .19 ] ], [ "easeOutCubic", [ .215, .61, .355, 1 ] ], [ "easeInOutCubic", [ .645, .045, .355, 1 ] ], [ "easeInQuart", [ .895, .03, .685, .22 ] ], [ "easeOutQuart", [ .165, .84, .44, 1 ] ], [ "easeInOutQuart", [ .77, 0, .175, 1 ] ], [ "easeInQuint", [ .755, .05, .855, .06 ] ], [ "easeOutQuint", [ .23, 1, .32, 1 ] ], [ "easeInOutQuint", [ .86, 0, .07, 1 ] ], [ "easeInExpo", [ .95, .05, .795, .035 ] ], [ "easeOutExpo", [ .19, 1, .22, 1 ] ], [ "easeInOutExpo", [ 1, 0, 0, 1 ] ], [ "easeInCirc", [ .6, .04, .98, .335 ] ], [ "easeOutCirc", [ .075, .82, .165, 1 ] ], [ "easeInOutCirc", [ .785, .135, .15, .86 ] ] ], function(e, t) {
                b.Easings[t[0]] = l.apply(null, t[1]);
            });
            var S = b.CSS = {
                RegEx: {
                    isHex: /^#([A-f\d]{3}){1,2}$/i,
                    valueUnwrap: /^[A-z]+\((.*)\)$/i,
                    wrappedValueAlreadyExtracted: /[0-9.]+ [0-9.]+ [0-9.]+( [0-9.]+)?/,
                    valueSplit: /([A-z]+\(.+\))|(([A-z0-9#-.]+?)(?=\s|$))/gi
                },
                Lists: {
                    colors: [ "fill", "stroke", "stopColor", "color", "backgroundColor", "borderColor", "borderTopColor", "borderRightColor", "borderBottomColor", "borderLeftColor", "outlineColor" ],
                    transformsBase: [ "translateX", "translateY", "scale", "scaleX", "scaleY", "skewX", "skewY", "rotateZ" ],
                    transforms3D: [ "transformPerspective", "translateZ", "scaleZ", "rotateX", "rotateY" ]
                },
                Hooks: {
                    templates: {
                        textShadow: [ "Color X Y Blur", "black 0px 0px 0px" ],
                        boxShadow: [ "Color X Y Blur Spread", "black 0px 0px 0px 0px" ],
                        clip: [ "Top Right Bottom Left", "0px 0px 0px 0px" ],
                        backgroundPosition: [ "X Y", "0% 0%" ],
                        transformOrigin: [ "X Y Z", "50% 50% 0px" ],
                        perspectiveOrigin: [ "X Y", "50% 50%" ]
                    },
                    registered: {},
                    register: function() {
                        for (var e = 0; e < S.Lists.colors.length; e++) {
                            var t = "color" === S.Lists.colors[e] ? "0 0 0 1" : "255 255 255 1";
                            S.Hooks.templates[S.Lists.colors[e]] = [ "Red Green Blue Alpha", t ];
                        }
                        var r, a, n;
                        if (d) for (r in S.Hooks.templates) {
                            n = (a = S.Hooks.templates[r])[0].split(" ");
                            var o = a[1].match(S.RegEx.valueSplit);
                            "Color" === n[0] && (n.push(n.shift()), o.push(o.shift()), S.Hooks.templates[r] = [ n.join(" "), o.join(" ") ]);
                        }
                        for (r in S.Hooks.templates) for (var e in n = (a = S.Hooks.templates[r])[0].split(" ")) {
                            var i = r + n[e], s = e;
                            S.Hooks.registered[i] = [ r, s ];
                        }
                    },
                    getRoot: function(e) {
                        var t = S.Hooks.registered[e];
                        return t ? t[0] : e;
                    },
                    cleanRootPropertyValue: function(e, t) {
                        return S.RegEx.valueUnwrap.test(t) && (t = t.match(S.RegEx.valueUnwrap)[1]), S.Values.isCSSNullValue(t) && (t = S.Hooks.templates[e][1]), 
                        t;
                    },
                    extractValue: function(e, t) {
                        var r = S.Hooks.registered[e];
                        if (r) {
                            var a = r[0], n = r[1];
                            return (t = S.Hooks.cleanRootPropertyValue(a, t)).toString().match(S.RegEx.valueSplit)[n];
                        }
                        return t;
                    },
                    injectValue: function(e, t, r) {
                        var a = S.Hooks.registered[e];
                        if (a) {
                            var n, i = a[0], s = a[1];
                            return (n = (r = S.Hooks.cleanRootPropertyValue(i, r)).toString().match(S.RegEx.valueSplit))[s] = t, 
                            n.join(" ");
                        }
                        return r;
                    }
                },
                Normalizations: {
                    registered: {
                        clip: function(e, t, r) {
                            switch (e) {
                              case "name":
                                return "clip";

                              case "extract":
                                var a;
                                return a = S.RegEx.wrappedValueAlreadyExtracted.test(r) ? r : (a = r.toString().match(S.RegEx.valueUnwrap)) ? a[1].replace(/,(\s+)?/g, " ") : r;

                              case "inject":
                                return "rect(" + r + ")";
                            }
                        },
                        blur: function(e, t, r) {
                            switch (e) {
                              case "name":
                                return b.State.isFirefox ? "filter" : "-webkit-filter";

                              case "extract":
                                var a = parseFloat(r);
                                if (!a && 0 !== a) {
                                    var n = r.toString().match(/blur\(([0-9]+[A-z]+)\)/i);
                                    a = n ? n[1] : 0;
                                }
                                return a;

                              case "inject":
                                return parseFloat(r) ? "blur(" + r + ")" : "none";
                            }
                        },
                        opacity: function(e, t, r) {
                            if (d <= 8) switch (e) {
                              case "name":
                                return "filter";

                              case "extract":
                                var a = r.toString().match(/alpha\(opacity=(.*)\)/i);
                                return a ? a[1] / 100 : 1;

                              case "inject":
                                return (t.style.zoom = 1) <= parseFloat(r) ? "" : "alpha(opacity=" + parseInt(100 * parseFloat(r), 10) + ")";
                            } else switch (e) {
                              case "name":
                                return "opacity";

                              case "extract":
                              case "inject":
                                return r;
                            }
                        }
                    },
                    register: function() {
                        d <= 9 || b.State.isGingerbread || (S.Lists.transformsBase = S.Lists.transformsBase.concat(S.Lists.transforms3D));
                        for (var e = 0; e < S.Lists.transformsBase.length; e++) !function() {
                            var t = S.Lists.transformsBase[e];
                            S.Normalizations.registered[t] = function(e, r, n) {
                                switch (e) {
                                  case "name":
                                    return "transform";

                                  case "extract":
                                    return i(r) === a || i(r).transformCache[t] === a ? /^scale/i.test(t) ? 1 : 0 : i(r).transformCache[t].replace(/[()]/g, "");

                                  case "inject":
                                    var o = !1;
                                    switch (t.substr(0, t.length - 1)) {
                                      case "translate":
                                        o = !/(%|px|em|rem|vw|vh|\d)$/i.test(n);
                                        break;

                                      case "scal":
                                      case "scale":
                                        b.State.isAndroid && i(r).transformCache[t] === a && n < 1 && (n = 1), o = !/(\d)$/i.test(n);
                                        break;

                                      case "skew":
                                        o = !/(deg|\d)$/i.test(n);
                                        break;

                                      case "rotate":
                                        o = !/(deg|\d)$/i.test(n);
                                    }
                                    return o || (i(r).transformCache[t] = "(" + n + ")"), i(r).transformCache[t];
                                }
                            };
                        }();
                        for (e = 0; e < S.Lists.colors.length; e++) !function() {
                            var t = S.Lists.colors[e];
                            S.Normalizations.registered[t] = function(e, r, n) {
                                switch (e) {
                                  case "name":
                                    return t;

                                  case "extract":
                                    var o;
                                    if (S.RegEx.wrappedValueAlreadyExtracted.test(n)) o = n; else {
                                        var i, s = {
                                            black: "rgb(0, 0, 0)",
                                            blue: "rgb(0, 0, 255)",
                                            gray: "rgb(128, 128, 128)",
                                            green: "rgb(0, 128, 0)",
                                            red: "rgb(255, 0, 0)",
                                            white: "rgb(255, 255, 255)"
                                        };
                                        /^[A-z]+$/i.test(n) ? i = s[n] !== a ? s[n] : s.black : S.RegEx.isHex.test(n) ? i = "rgb(" + S.Values.hexToRgb(n).join(" ") + ")" : /^rgba?\(/i.test(n) || (i = s.black), 
                                        o = (i || n).toString().match(S.RegEx.valueUnwrap)[1].replace(/,(\s+)?/g, " ");
                                    }
                                    return d <= 8 || 3 !== o.split(" ").length || (o += " 1"), o;

                                  case "inject":
                                    return d <= 8 ? 4 === n.split(" ").length && (n = n.split(/\s+/).slice(0, 3).join(" ")) : 3 === n.split(" ").length && (n += " 1"), 
                                    (d <= 8 ? "rgb" : "rgba") + "(" + n.replace(/\s+/g, ",").replace(/\.(\d)+(?=,)/g, "") + ")";
                                }
                            };
                        }();
                    }
                },
                Names: {
                    camelCase: function(e) {
                        return e.replace(/-(\w)/g, function(e, t) {
                            return t.toUpperCase();
                        });
                    },
                    SVGAttribute: function(e) {
                        var t = "width|height|x|y|cx|cy|r|rx|ry|x1|x2|y1|y2";
                        return (d || b.State.isAndroid && !b.State.isChrome) && (t += "|transform"), new RegExp("^(" + t + ")$", "i").test(e);
                    },
                    prefixCheck: function(e) {
                        if (b.State.prefixMatches[e]) return [ b.State.prefixMatches[e], !0 ];
                        for (var t = [ "", "Webkit", "Moz", "ms", "O" ], r = 0, a = t.length; r < a; r++) {
                            var n;
                            if (n = 0 === r ? e : t[r] + e.replace(/^\w/, function(e) {
                                return e.toUpperCase();
                            }), m.isString(b.State.prefixElement.style[n])) return [ b.State.prefixMatches[e] = n, !0 ];
                        }
                        return [ e, !1 ];
                    }
                },
                Values: {
                    hexToRgb: function(e) {
                        var t;
                        return e = e.replace(/^#?([a-f\d])([a-f\d])([a-f\d])$/i, function(e, t, r, a) {
                            return t + t + r + r + a + a;
                        }), (t = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(e)) ? [ parseInt(t[1], 16), parseInt(t[2], 16), parseInt(t[3], 16) ] : [ 0, 0, 0 ];
                    },
                    isCSSNullValue: function(e) {
                        return 0 == e || /^(none|auto|transparent|(rgba\(0, ?0, ?0, ?0\)))$/i.test(e);
                    },
                    getUnitType: function(e) {
                        return /^(rotate|skew)/i.test(e) ? "deg" : /(^(scale|scaleX|scaleY|scaleZ|alpha|flexGrow|flexHeight|zIndex|fontWeight)$)|((opacity|red|green|blue|alpha)$)/i.test(e) ? "" : "px";
                    },
                    getDisplayType: function(e) {
                        var t = e && e.tagName.toString().toLowerCase();
                        return /^(b|big|i|small|tt|abbr|acronym|cite|code|dfn|em|kbd|strong|samp|var|a|bdo|br|img|map|object|q|script|span|sub|sup|button|input|label|select|textarea)$/i.test(t) ? "inline" : /^(li)$/i.test(t) ? "list-item" : /^(tr)$/i.test(t) ? "table-row" : /^(table)$/i.test(t) ? "table" : /^(tbody)$/i.test(t) ? "table-row-group" : "block";
                    },
                    addClass: function(e, t) {
                        e.classList ? e.classList.add(t) : e.className += (e.className.length ? " " : "") + t;
                    },
                    removeClass: function(e, t) {
                        e.classList ? e.classList.remove(t) : e.className = e.className.toString().replace(new RegExp("(^|\\s)" + t.split(" ").join("|") + "(\\s|$)", "gi"), " ");
                    }
                },
                getPropertyValue: function(e, r, n, o) {
                    function s(e, r) {
                        function n() {
                            u && S.setPropertyValue(e, "display", "none");
                        }
                        var l = 0;
                        if (d <= 8) l = f.css(e, r); else {
                            var g, u = !1;
                            if (/^(width|height)$/.test(r) && 0 === S.getPropertyValue(e, "display") && (u = !0, 
                            S.setPropertyValue(e, "display", S.Values.getDisplayType(e))), !o) {
                                if ("height" === r && "border-box" !== S.getPropertyValue(e, "boxSizing").toString().toLowerCase()) {
                                    var c = e.offsetHeight - (parseFloat(S.getPropertyValue(e, "borderTopWidth")) || 0) - (parseFloat(S.getPropertyValue(e, "borderBottomWidth")) || 0) - (parseFloat(S.getPropertyValue(e, "paddingTop")) || 0) - (parseFloat(S.getPropertyValue(e, "paddingBottom")) || 0);
                                    return n(), c;
                                }
                                if ("width" === r && "border-box" !== S.getPropertyValue(e, "boxSizing").toString().toLowerCase()) {
                                    var p = e.offsetWidth - (parseFloat(S.getPropertyValue(e, "borderLeftWidth")) || 0) - (parseFloat(S.getPropertyValue(e, "borderRightWidth")) || 0) - (parseFloat(S.getPropertyValue(e, "paddingLeft")) || 0) - (parseFloat(S.getPropertyValue(e, "paddingRight")) || 0);
                                    return n(), p;
                                }
                            }
                            g = i(e) === a ? t.getComputedStyle(e, null) : i(e).computedStyle ? i(e).computedStyle : i(e).computedStyle = t.getComputedStyle(e, null), 
                            "borderColor" === r && (r = "borderTopColor"), ("" === (l = 9 === d && "filter" === r ? g.getPropertyValue(r) : g[r]) || null === l) && (l = e.style[r]), 
                            n();
                        }
                        if ("auto" === l && /^(top|right|bottom|left)$/i.test(r)) {
                            var m = s(e, "position");
                            ("fixed" === m || "absolute" === m && /top|left/i.test(r)) && (l = f(e).position()[r] + "px");
                        }
                        return l;
                    }
                    var l;
                    if (S.Hooks.registered[r]) {
                        var u = r, c = S.Hooks.getRoot(u);
                        n === a && (n = S.getPropertyValue(e, S.Names.prefixCheck(c)[0])), S.Normalizations.registered[c] && (n = S.Normalizations.registered[c]("extract", e, n)), 
                        l = S.Hooks.extractValue(u, n);
                    } else if (S.Normalizations.registered[r]) {
                        var p, g;
                        "transform" !== (p = S.Normalizations.registered[r]("name", e)) && (g = s(e, S.Names.prefixCheck(p)[0]), 
                        S.Values.isCSSNullValue(g) && S.Hooks.templates[r] && (g = S.Hooks.templates[r][1])), 
                        l = S.Normalizations.registered[r]("extract", e, g);
                    }
                    if (!/^[\d-]/.test(l)) if (i(e) && i(e).isSVG && S.Names.SVGAttribute(r)) if (/^(height|width)$/i.test(r)) try {
                        l = e.getBBox()[r];
                    } catch (m) {
                        l = 0;
                    } else l = e.getAttribute(r); else l = s(e, S.Names.prefixCheck(r)[0]);
                    return S.Values.isCSSNullValue(l) && (l = 0), 2 <= b.debug && console.log("Get " + r + ": " + l), 
                    l;
                },
                setPropertyValue: function(e, r, a, n, o) {
                    var s = r;
                    if ("scroll" === r) o.container ? o.container["scroll" + o.direction] = a : "Left" === o.direction ? t.scrollTo(a, o.alternateValue) : t.scrollTo(o.alternateValue, a); else if (S.Normalizations.registered[r] && "transform" === S.Normalizations.registered[r]("name", e)) S.Normalizations.registered[r]("inject", e, a), 
                    s = "transform", a = i(e).transformCache[r]; else {
                        if (S.Hooks.registered[r]) {
                            var l = r, u = S.Hooks.getRoot(r);
                            n = n || S.getPropertyValue(e, u), a = S.Hooks.injectValue(l, a, n), r = u;
                        }
                        if (S.Normalizations.registered[r] && (a = S.Normalizations.registered[r]("inject", e, a), 
                        r = S.Normalizations.registered[r]("name", e)), s = S.Names.prefixCheck(r)[0], d <= 8) try {
                            e.style[s] = a;
                        } catch (c) {
                            b.debug && console.log("Browser does not support [" + a + "] for [" + s + "]");
                        } else i(e) && i(e).isSVG && S.Names.SVGAttribute(r) ? e.setAttribute(r, a) : e.style[s] = a;
                        2 <= b.debug && console.log("Set " + r + " (" + s + "): " + a);
                    }
                    return [ s, a ];
                },
                flushTransformCache: function(e) {
                    function t(t) {
                        return parseFloat(S.getPropertyValue(e, t));
                    }
                    var r = "";
                    if ((d || b.State.isAndroid && !b.State.isChrome) && i(e).isSVG) {
                        var a = {
                            translate: [ t("translateX"), t("translateY") ],
                            skewX: [ t("skewX") ],
                            skewY: [ t("skewY") ],
                            scale: 1 !== t("scale") ? [ t("scale"), t("scale") ] : [ t("scaleX"), t("scaleY") ],
                            rotate: [ t("rotateZ"), 0, 0 ]
                        };
                        f.each(i(e).transformCache, function(e) {
                            /^translate/i.test(e) ? e = "translate" : /^scale/i.test(e) ? e = "scale" : /^rotate/i.test(e) && (e = "rotate"), 
                            a[e] && (r += e + "(" + a[e].join(" ") + ") ", delete a[e]);
                        });
                    } else {
                        var n, o;
                        f.each(i(e).transformCache, function(t) {
                            return n = i(e).transformCache[t], "transformPerspective" === t ? (o = n, !0) : (9 === d && "rotateZ" === t && (t = "rotate"), 
                            void (r += t + n + " "));
                        }), o && (r = "perspective" + o + " " + r);
                    }
                    S.setPropertyValue(e, "transform", r);
                }
            };
            S.Hooks.register(), S.Normalizations.register(), b.hook = function(e, t, r) {
                var n = a;
                return e = o(e), f.each(e, function(e, o) {
                    if (i(o) === a && b.init(o), r === a) n === a && (n = b.CSS.getPropertyValue(o, t)); else {
                        var s = b.CSS.setPropertyValue(o, t, r);
                        "transform" === s[0] && b.CSS.flushTransformCache(o), n = s;
                    }
                }), n;
            };
            var P = function() {
                function e() {
                    return s ? k.promise || null : l;
                }
                function n() {
                    function e(e) {
                        function p(e, t) {
                            var r = a, n = a, i = a;
                            return m.isArray(e) ? (r = e[0], !m.isArray(e[1]) && /^[\d-]/.test(e[1]) || m.isFunction(e[1]) || S.RegEx.isHex.test(e[1]) ? i = e[1] : (m.isString(e[1]) && !S.RegEx.isHex.test(e[1]) || m.isArray(e[1])) && (n = t ? e[1] : u(e[1], s.duration), 
                            e[2] !== a && (i = e[2]))) : r = e, t || (n = n || s.easing), m.isFunction(r) && (r = r.call(o, V, w)), 
                            m.isFunction(i) && (i = i.call(o, V, w)), [ r || 0, n, i ];
                        }
                        function d(e, t) {
                            var r, a;
                            return a = (t || "0").toString().toLowerCase().replace(/[%A-z]+$/, function(e) {
                                return r = e, "";
                            }), r || (r = S.Values.getUnitType(e)), [ a, r ];
                        }
                        function h() {
                            var e = {
                                myParent: o.parentNode || r.body,
                                position: S.getPropertyValue(o, "position"),
                                fontSize: S.getPropertyValue(o, "fontSize")
                            }, a = e.position === L.lastPosition && e.myParent === L.lastParent, n = e.fontSize === L.lastFontSize;
                            L.lastParent = e.myParent, L.lastPosition = e.position, L.lastFontSize = e.fontSize;
                            var s = 100, l = {};
                            if (n && a) l.emToPx = L.lastEmToPx, l.percentToPxWidth = L.lastPercentToPxWidth, 
                            l.percentToPxHeight = L.lastPercentToPxHeight; else {
                                var u = i(o).isSVG ? r.createElementNS("http://www.w3.org/2000/svg", "rect") : r.createElement("div");
                                b.init(u), e.myParent.appendChild(u), f.each([ "overflow", "overflowX", "overflowY" ], function(e, t) {
                                    b.CSS.setPropertyValue(u, t, "hidden");
                                }), b.CSS.setPropertyValue(u, "position", e.position), b.CSS.setPropertyValue(u, "fontSize", e.fontSize), 
                                b.CSS.setPropertyValue(u, "boxSizing", "content-box"), f.each([ "minWidth", "maxWidth", "width", "minHeight", "maxHeight", "height" ], function(e, t) {
                                    b.CSS.setPropertyValue(u, t, s + "%");
                                }), b.CSS.setPropertyValue(u, "paddingLeft", s + "em"), l.percentToPxWidth = L.lastPercentToPxWidth = (parseFloat(S.getPropertyValue(u, "width", null, !0)) || 1) / s, 
                                l.percentToPxHeight = L.lastPercentToPxHeight = (parseFloat(S.getPropertyValue(u, "height", null, !0)) || 1) / s, 
                                l.emToPx = L.lastEmToPx = (parseFloat(S.getPropertyValue(u, "paddingLeft")) || 1) / s, 
                                e.myParent.removeChild(u);
                            }
                            return null === L.remToPx && (L.remToPx = parseFloat(S.getPropertyValue(r.body, "fontSize")) || 16), 
                            null === L.vwToPx && (L.vwToPx = parseFloat(t.innerWidth) / 100, L.vhToPx = parseFloat(t.innerHeight) / 100), 
                            l.remToPx = L.remToPx, l.vwToPx = L.vwToPx, l.vhToPx = L.vhToPx, 1 <= b.debug && console.log("Unit ratios: " + JSON.stringify(l), o), 
                            l;
                        }
                        if (s.begin && 0 === V) try {
                            s.begin.call(g, g);
                        } catch (x) {
                            setTimeout(function() {
                                throw x;
                            }, 1);
                        }
                        if ("scroll" === A) {
                            var P, C, T, F = /^x$/i.test(s.axis) ? "Left" : "Top", j = parseFloat(s.offset) || 0;
                            s.container ? m.isWrapped(s.container) || m.isNode(s.container) ? (s.container = s.container[0] || s.container, 
                            T = (P = s.container["scroll" + F]) + f(o).position()[F.toLowerCase()] + j) : s.container = null : (P = b.State.scrollAnchor[b.State["scrollProperty" + F]], 
                            C = b.State.scrollAnchor[b.State["scrollProperty" + ("Left" === F ? "Top" : "Left")]], 
                            T = f(o).offset()[F.toLowerCase()] + j), l = {
                                scroll: {
                                    rootPropertyValue: !1,
                                    startValue: P,
                                    currentValue: P,
                                    endValue: T,
                                    unitType: "",
                                    easing: s.easing,
                                    scrollData: {
                                        container: s.container,
                                        direction: F,
                                        alternateValue: C
                                    }
                                },
                                element: o
                            }, b.debug && console.log("tweensContainer (scroll): ", l.scroll, o);
                        } else if ("reverse" === A) {
                            if (!i(o).tweensContainer) return void f.dequeue(o, s.queue);
                            "none" === i(o).opts.display && (i(o).opts.display = "auto"), "hidden" === i(o).opts.visibility && (i(o).opts.visibility = "visible"), 
                            i(o).opts.loop = !1, i(o).opts.begin = null, i(o).opts.complete = null, v.easing || delete s.easing, 
                            v.duration || delete s.duration, s = f.extend({}, i(o).opts, s);
                            var E = f.extend(!0, {}, i(o).tweensContainer);
                            for (var H in E) if ("element" !== H) {
                                var N = E[H].startValue;
                                E[H].startValue = E[H].currentValue = E[H].endValue, E[H].endValue = N, m.isEmptyObject(v) || (E[H].easing = s.easing), 
                                b.debug && console.log("reverse tweensContainer (" + H + "): " + JSON.stringify(E[H]), o);
                            }
                            l = E;
                        } else if ("start" === A) {
                            for (var z in i(o).tweensContainer && !0 === i(o).isAnimating && (E = i(o).tweensContainer), 
                            f.each(y, function(e, t) {
                                if (RegExp("^" + S.Lists.colors.join("$|^") + "$").test(e)) {
                                    var r = p(t, !0), n = r[0], o = r[1], i = r[2];
                                    if (S.RegEx.isHex.test(n)) {
                                        for (var s = [ "Red", "Green", "Blue" ], l = S.Values.hexToRgb(n), u = i ? S.Values.hexToRgb(i) : a, c = 0; c < s.length; c++) {
                                            var f = [ l[c] ];
                                            o && f.push(o), u !== a && f.push(u[c]), y[e + s[c]] = f;
                                        }
                                        delete y[e];
                                    }
                                }
                            }), y) {
                                var O = p(y[z]), q = O[0], $ = O[1], M = O[2];
                                z = S.Names.camelCase(z);
                                var I = S.Hooks.getRoot(z), B = !1;
                                if (i(o).isSVG || "tween" === I || !1 !== S.Names.prefixCheck(I)[1] || S.Normalizations.registered[I] !== a) {
                                    (s.display !== a && null !== s.display && "none" !== s.display || s.visibility !== a && "hidden" !== s.visibility) && /opacity|filter/.test(z) && !M && 0 !== q && (M = 0), 
                                    s._cacheValues && E && E[z] ? (M === a && (M = E[z].endValue + E[z].unitType), B = i(o).rootPropertyValueCache[I]) : S.Hooks.registered[z] ? M === a ? (B = S.getPropertyValue(o, I), 
                                    M = S.getPropertyValue(o, z, B)) : B = S.Hooks.templates[I][1] : M === a && (M = S.getPropertyValue(o, z));
                                    var W, G, Y, D = !1;
                                    if (M = (W = d(z, M))[0], Y = W[1], q = (W = d(z, q))[0].replace(/^([+-\/*])=/, function(e, t) {
                                        return D = t, "";
                                    }), G = W[1], M = parseFloat(M) || 0, q = parseFloat(q) || 0, "%" === G && (/^(fontSize|lineHeight)$/.test(z) ? (q /= 100, 
                                    G = "em") : /^scale/.test(z) ? (q /= 100, G = "") : /(Red|Green|Blue)$/i.test(z) && (q = q / 100 * 255, 
                                    G = "")), /[\/*]/.test(D)) G = Y; else if (Y !== G && 0 !== M) if (0 === q) G = Y; else {
                                        n = n || h();
                                        var Q = /margin|padding|left|right|width|text|word|letter/i.test(z) || /X$/.test(z) || "x" === z ? "x" : "y";
                                        switch (Y) {
                                          case "%":
                                            M *= "x" === Q ? n.percentToPxWidth : n.percentToPxHeight;
                                            break;

                                          case "px":
                                            break;

                                          default:
                                            M *= n[Y + "ToPx"];
                                        }
                                        switch (G) {
                                          case "%":
                                            M *= 1 / ("x" === Q ? n.percentToPxWidth : n.percentToPxHeight);
                                            break;

                                          case "px":
                                            break;

                                          default:
                                            M *= 1 / n[G + "ToPx"];
                                        }
                                    }
                                    switch (D) {
                                      case "+":
                                        q = M + q;
                                        break;

                                      case "-":
                                        q = M - q;
                                        break;

                                      case "*":
                                        q *= M;
                                        break;

                                      case "/":
                                        q = M / q;
                                    }
                                    l[z] = {
                                        rootPropertyValue: B,
                                        startValue: M,
                                        currentValue: M,
                                        endValue: q,
                                        unitType: G,
                                        easing: $
                                    }, b.debug && console.log("tweensContainer (" + z + "): " + JSON.stringify(l[z]), o);
                                } else b.debug && console.log("Skipping [" + I + "] due to a lack of browser support.");
                            }
                            l.element = o;
                        }
                        l.element && (S.Values.addClass(o, "velocity-animating"), R.push(l), "" === s.queue && (i(o).tweensContainer = l, 
                        i(o).opts = s), i(o).isAnimating = !0, V === w - 1 ? (b.State.calls.push([ R, g, s, null, k.resolver ]), 
                        !1 === b.State.isTicking && (b.State.isTicking = !0, c())) : V++);
                    }
                    var n, o = this, s = f.extend({}, b.defaults, v), l = {};
                    switch (i(o) === a && b.init(o), parseFloat(s.delay) && !1 !== s.queue && f.queue(o, s.queue, function(e) {
                        b.velocityQueueEntryFlag = !0, i(o).delayTimer = {
                            setTimeout: setTimeout(e, parseFloat(s.delay)),
                            next: e
                        };
                    }), s.duration.toString().toLowerCase()) {
                      case "fast":
                        s.duration = 200;
                        break;

                      case "normal":
                        s.duration = 400;
                        break;

                      case "slow":
                        s.duration = 600;
                        break;

                      default:
                        s.duration = parseFloat(s.duration) || 1;
                    }
                    !1 !== b.mock && (!0 === b.mock ? s.duration = s.delay = 1 : (s.duration *= parseFloat(b.mock) || 1, 
                    s.delay *= parseFloat(b.mock) || 1)), s.easing = u(s.easing, s.duration), s.begin && !m.isFunction(s.begin) && (s.begin = null), 
                    s.progress && !m.isFunction(s.progress) && (s.progress = null), s.complete && !m.isFunction(s.complete) && (s.complete = null), 
                    s.display !== a && null !== s.display && (s.display = s.display.toString().toLowerCase(), 
                    "auto" === s.display && (s.display = b.CSS.Values.getDisplayType(o))), s.visibility !== a && null !== s.visibility && (s.visibility = s.visibility.toString().toLowerCase()), 
                    s.mobileHA = s.mobileHA && b.State.isMobile && !b.State.isGingerbread, !1 === s.queue ? s.delay ? setTimeout(e, s.delay) : e() : f.queue(o, s.queue, function(t, r) {
                        return !0 === r ? (k.promise && k.resolver(g), !0) : (b.velocityQueueEntryFlag = !0, 
                        void e());
                    }), "" !== s.queue && "fx" !== s.queue || "inprogress" === f.queue(o)[0] || f.dequeue(o);
                }
                var s, l, d, g, y, v, x = arguments[0] && (arguments[0].p || f.isPlainObject(arguments[0].properties) && !arguments[0].properties.names || m.isString(arguments[0].properties));
                if (m.isWrapped(this) ? (s = !1, d = 0, l = g = this) : (s = !0, d = 1, g = x ? arguments[0].elements || arguments[0].e : arguments[0]), 
                g = o(g)) {
                    v = x ? (y = arguments[0].properties || arguments[0].p, arguments[0].options || arguments[0].o) : (y = arguments[d], 
                    arguments[d + 1]);
                    var w = g.length, V = 0;
                    if (!/^(stop|finish)$/i.test(y) && !f.isPlainObject(v)) {
                        v = {};
                        for (var T = d + 1; T < arguments.length; T++) m.isArray(arguments[T]) || !/^(fast|normal|slow)$/i.test(arguments[T]) && !/^\d/.test(arguments[T]) ? m.isString(arguments[T]) || m.isArray(arguments[T]) ? v.easing = arguments[T] : m.isFunction(arguments[T]) && (v.complete = arguments[T]) : v.duration = arguments[T];
                    }
                    var A, k = {
                        promise: null,
                        resolver: null,
                        rejecter: null
                    };
                    switch (s && b.Promise && (k.promise = new b.Promise(function(e, t) {
                        k.resolver = e, k.rejecter = t;
                    })), y) {
                      case "scroll":
                        A = "scroll";
                        break;

                      case "reverse":
                        A = "reverse";
                        break;

                      case "finish":
                      case "stop":
                        f.each(g, function(e, t) {
                            i(t) && i(t).delayTimer && (clearTimeout(i(t).delayTimer.setTimeout), i(t).delayTimer.next && i(t).delayTimer.next(), 
                            delete i(t).delayTimer);
                        });
                        var F = [];
                        return f.each(b.State.calls, function(e, t) {
                            t && f.each(t[1], function(r, n) {
                                var o = v === a ? "" : v;
                                return !0 !== o && t[2].queue !== o && (v !== a || !1 !== t[2].queue) || void f.each(g, function(r, a) {
                                    a === n && ((!0 === v || m.isString(v)) && (f.each(f.queue(a, m.isString(v) ? v : ""), function(e, t) {
                                        m.isFunction(t) && t(null, !0);
                                    }), f.queue(a, m.isString(v) ? v : "", [])), "stop" === y ? (i(a) && i(a).tweensContainer && !1 !== o && f.each(i(a).tweensContainer, function(e, t) {
                                        t.endValue = t.currentValue;
                                    }), F.push(e)) : "finish" === y && (t[2].duration = 1));
                                });
                            });
                        }), "stop" === y && (f.each(F, function(e, t) {
                            p(t, !0);
                        }), k.promise && k.resolver(g)), e();

                      default:
                        if (!f.isPlainObject(y) || m.isEmptyObject(y)) {
                            if (m.isString(y) && b.Redirects[y]) {
                                var E = (j = f.extend({}, v)).duration, H = j.delay || 0;
                                return !0 === j.backwards && (g = f.extend(!0, [], g).reverse()), f.each(g, function(e, t) {
                                    parseFloat(j.stagger) ? j.delay = H + parseFloat(j.stagger) * e : m.isFunction(j.stagger) && (j.delay = H + j.stagger.call(t, e, w)), 
                                    j.drag && (j.duration = parseFloat(E) || (/^(callout|transition)/.test(y) ? 1e3 : 400), 
                                    j.duration = Math.max(j.duration * (j.backwards ? 1 - e / w : (e + 1) / w), .75 * j.duration, 200)), 
                                    b.Redirects[y].call(t, t, j || {}, e, w, g, k.promise ? k : a);
                                }), e();
                            }
                            var N = "Velocity: First argument (" + y + ") was not a property map, a known action, or a registered redirect. Aborting.";
                            return k.promise ? k.rejecter(new Error(N)) : console.log(N), e();
                        }
                        A = "start";
                    }
                    var z, j, L = {
                        lastParent: null,
                        lastPosition: null,
                        lastFontSize: null,
                        lastPercentToPxWidth: null,
                        lastPercentToPxHeight: null,
                        lastEmToPx: null,
                        remToPx: null,
                        vwToPx: null,
                        vhToPx: null
                    }, R = [];
                    if (f.each(g, function(e, t) {
                        m.isNode(t) && n.call(t);
                    }), (j = f.extend({}, b.defaults, v)).loop = parseInt(j.loop), z = 2 * j.loop - 1, 
                    j.loop) for (var O = 0; O < z; O++) {
                        var q = {
                            delay: j.delay,
                            progress: j.progress
                        };
                        O === z - 1 && (q.display = j.display, q.visibility = j.visibility, q.complete = j.complete), 
                        P(g, "reverse", q);
                    }
                    return e();
                }
            };
            (b = f.extend(P, b)).animate = P;
            var w = t.requestAnimationFrame || g;
            return b.State.isMobile || r.hidden === a || r.addEventListener("visibilitychange", function() {
                r.hidden ? (w = function(e) {
                    return setTimeout(function() {
                        e(!0);
                    }, 16);
                }, c()) : w = t.requestAnimationFrame || g;
            }), e.Velocity = b, e !== t && (e.fn.velocity = P, e.fn.velocity.defaults = b.defaults), 
            f.each([ "Down", "Up" ], function(e, t) {
                b.Redirects["slide" + t] = function(e, r, n, o, i, s) {
                    var l = f.extend({}, r), u = l.begin, c = l.complete, p = {
                        height: "",
                        marginTop: "",
                        marginBottom: "",
                        paddingTop: "",
                        paddingBottom: ""
                    }, d = {};
                    l.display === a && (l.display = "Down" === t ? "inline" === b.CSS.Values.getDisplayType(e) ? "inline-block" : "block" : "none"), 
                    l.begin = function() {
                        for (var r in u && u.call(i, i), p) {
                            d[r] = e.style[r];
                            var a = b.CSS.getPropertyValue(e, r);
                            p[r] = "Down" === t ? [ a, 0 ] : [ 0, a ];
                        }
                        d.overflow = e.style.overflow, e.style.overflow = "hidden";
                    }, l.complete = function() {
                        for (var t in d) e.style[t] = d[t];
                        c && c.call(i, i), s && s.resolver(i);
                    }, b(e, p, l);
                };
            }), f.each([ "In", "Out" ], function(e, t) {
                b.Redirects["fade" + t] = function(e, r, n, o, i, s) {
                    var l = f.extend({}, r), u = {
                        opacity: "In" === t ? 1 : 0
                    }, c = l.complete;
                    l.complete = n !== o - 1 ? l.begin = null : function() {
                        c && c.call(i, i), s && s.resolver(i);
                    }, l.display === a && (l.display = "In" === t ? "auto" : "none"), b(this, u, l);
                };
            }), b;
        }
        jQuery.fn.velocity = jQuery.fn.animate;
    }(window.jQuery || window.Zepto || window, window, document);
})), jQuery.extend(jQuery.easing, {
    easeInOutMaterial: function(x, t, b, c, d) {
        return (t /= d / 2) < 1 ? c / 2 * t * t + b : c / 4 * ((t -= 2) * t * t + 2) + b;
    }
}), function($) {
    $(document).ready(function() {
        $.fn.reverse = [].reverse, $(document).on("mouseenter.fixedActionBtn", ".fixed-action-btn:not(.click-to-toggle):not(.toolbar)", function(e) {
            var $this = $(this);
            openFABMenu($this);
        }), $(document).on("mouseleave.fixedActionBtn", ".fixed-action-btn:not(.click-to-toggle):not(.toolbar)", function(e) {
            var $this = $(this);
            closeFABMenu($this);
        }), $(document).on("click.fabClickToggle", ".fixed-action-btn.click-to-toggle > a", function(e) {
            var $menu = $(this).parent();
            $menu.hasClass("active") ? closeFABMenu($menu) : openFABMenu($menu);
        }), $(document).on("click.fabToolbar", ".fixed-action-btn.toolbar > a", function(e) {
            var $menu = $(this).parent();
            FABtoToolbar($menu);
        });
    }), $.fn.extend({
        openFAB: function() {
            openFABMenu($(this));
        },
        closeFAB: function() {
            closeFABMenu($(this));
        },
        openToolbar: function() {
            FABtoToolbar($(this));
        },
        closeToolbar: function() {
            toolbarToFAB($(this));
        }
    });
    var openFABMenu = function(btn) {
        var $this = btn;
        if (!1 === $this.hasClass("active")) {
            var offsetY, offsetX;
            !0 === $this.hasClass("horizontal") ? offsetX = 40 : offsetY = 40, $this.addClass("active"), 
            $this.find("ul .btn-floating").velocity({
                scaleY: ".4",
                scaleX: ".4",
                translateY: offsetY + "px",
                translateX: offsetX + "px"
            }, {
                duration: 0
            });
            var time = 0;
            $this.find("ul .btn-floating").reverse().each(function() {
                $(this).velocity({
                    opacity: "1",
                    scaleX: "1",
                    scaleY: "1",
                    translateY: "0",
                    translateX: "0"
                }, {
                    duration: 80,
                    delay: time
                }), time += 40;
            });
        }
    }, closeFABMenu = function(btn) {
        var offsetY, offsetX, $this = btn;
        !0 === $this.hasClass("horizontal") ? offsetX = 40 : offsetY = 40, $this.removeClass("active");
        $this.find("ul .btn-floating").velocity("stop", !0), $this.find("ul .btn-floating").velocity({
            opacity: "0",
            scaleX: ".4",
            scaleY: ".4",
            translateY: offsetY + "px",
            translateX: offsetX + "px"
        }, {
            duration: 80
        });
    }, FABtoToolbar = function(btn) {
        if ("true" !== btn.attr("data-open")) {
            var offsetX, offsetY, scaleFactor, windowWidth = window.innerWidth, windowHeight = window.innerHeight, btnRect = btn[0].getBoundingClientRect(), anchor = btn.find("> a").first(), menu = btn.find("> ul").first(), backdrop = $('<div class="fab-backdrop"></div>'), fabColor = anchor.css("background-color");
            anchor.append(backdrop), offsetX = btnRect.left - windowWidth / 2 + btnRect.width / 2, 
            offsetY = windowHeight - btnRect.bottom, scaleFactor = windowWidth / backdrop.width(), 
            btn.attr("data-origin-bottom", btnRect.bottom), btn.attr("data-origin-left", btnRect.left), 
            btn.attr("data-origin-width", btnRect.width), btn.addClass("active"), btn.attr("data-open", !0), 
            btn.css({
                "text-align": "center",
                width: "100%",
                bottom: 0,
                left: 0,
                transform: "translateX(" + offsetX + "px)",
                transition: "none"
            }), anchor.css({
                transform: "translateY(" + -offsetY + "px)",
                transition: "none"
            }), backdrop.css({
                "background-color": fabColor
            }), setTimeout(function() {
                btn.css({
                    transform: "",
                    transition: "transform .2s cubic-bezier(0.550, 0.085, 0.680, 0.530), background-color 0s linear .2s"
                }), anchor.css({
                    overflow: "visible",
                    transform: "",
                    transition: "transform .2s"
                }), setTimeout(function() {
                    btn.css({
                        overflow: "hidden",
                        "background-color": fabColor
                    }), backdrop.css({
                        transform: "scale(" + scaleFactor + ")",
                        transition: "transform .2s cubic-bezier(0.550, 0.055, 0.675, 0.190)"
                    }), menu.find("> li > a").css({
                        opacity: 1
                    }), $(window).on("scroll.fabToolbarClose", function() {
                        toolbarToFAB(btn), $(window).off("scroll.fabToolbarClose"), $(document).off("click.fabToolbarClose");
                    }), $(document).on("click.fabToolbarClose", function(e) {
                        $(e.target).closest(menu).length || (toolbarToFAB(btn), $(window).off("scroll.fabToolbarClose"), 
                        $(document).off("click.fabToolbarClose"));
                    });
                }, 100);
            }, 0);
        }
    }, toolbarToFAB = function(btn) {
        if ("true" === btn.attr("data-open")) {
            var offsetX, offsetY, windowWidth = window.innerWidth, windowHeight = window.innerHeight, btnWidth = btn.attr("data-origin-width"), btnBottom = btn.attr("data-origin-bottom"), btnLeft = btn.attr("data-origin-left"), anchor = btn.find("> .btn-floating").first(), menu = btn.find("> ul").first(), backdrop = btn.find(".fab-backdrop"), fabColor = anchor.css("background-color");
            offsetX = btnLeft - windowWidth / 2 + btnWidth / 2, offsetY = windowHeight - btnBottom, 
            windowWidth / backdrop.width(), btn.removeClass("active"), btn.attr("data-open", !1), 
            btn.css({
                "background-color": "transparent",
                transition: "none"
            }), anchor.css({
                transition: "none"
            }), backdrop.css({
                transform: "scale(0)",
                "background-color": fabColor
            }), menu.find("> li > a").css({
                opacity: ""
            }), setTimeout(function() {
                backdrop.remove(), btn.css({
                    "text-align": "",
                    width: "",
                    bottom: "",
                    left: "",
                    overflow: "",
                    "background-color": "",
                    transform: "translate3d(" + -offsetX + "px,0,0)"
                }), anchor.css({
                    overflow: "",
                    transform: "translate3d(0," + offsetY + "px,0)"
                }), setTimeout(function() {
                    btn.css({
                        transform: "translate3d(0,0,0)",
                        transition: "transform .2s"
                    }), anchor.css({
                        transform: "translate3d(0,0,0)",
                        transition: "transform .2s cubic-bezier(0.550, 0.055, 0.675, 0.190)"
                    });
                }, 20);
            }, 200);
        }
    };
}(jQuery), function($) {
    $(document).ready(function() {
        $(document).on("click.card", ".card", function(e) {
            if ($(this).find("> .card-reveal").length) {
                var $card = $(e.target).closest(".card");
                void 0 === $card.data("initialOverflow") && $card.data("initialOverflow", void 0 === $card.css("overflow") ? "" : $card.css("overflow")), 
                $(e.target).is($(".card-reveal .card-title")) || $(e.target).is($(".card-reveal .card-title i")) ? $(this).find(".card-reveal").velocity({
                    translateY: 0
                }, {
                    duration: 225,
                    queue: !1,
                    easing: "easeInOutQuad",
                    complete: function() {
                        $(this).css({
                            display: "none"
                        }), $card.css("overflow", $card.data("initialOverflow"));
                    }
                }) : ($(e.target).is($(".card .activator")) || $(e.target).is($(".card .activator i"))) && ($card.css("overflow", "hidden"), 
                $(this).find(".card-reveal").css({
                    display: "block"
                }).velocity("stop", !1).velocity({
                    translateY: "-100%"
                }, {
                    duration: 300,
                    queue: !1,
                    easing: "easeInOutQuad"
                }));
            }
        });
    });
}(jQuery), function($) {
    var methods = {
        init: function(options) {
            options = $.extend({
                duration: 200,
                dist: -100,
                shift: 0,
                padding: 0,
                fullWidth: !1,
                indicators: !1,
                noWrap: !1,
                onCycleTo: null
            }, options);
            var namespace = Materialize.objectSelectorString($(this));
            return this.each(function(i) {
                var images, item_width, item_height, offset, center, pressed, dim, count, reference, referenceY, amplitude, target, velocity, xform, frame, timestamp, ticker, dragged, vertical_dragged, $indicators = $('<ul class="indicators"></ul>'), scrollingTimeout = null, oneTimeCallback = null, view = $(this), hasMultipleSlides = 1 < view.find(".carousel-item").length, showIndicators = (view.attr("data-indicators") || options.indicators) && hasMultipleSlides, noWrap = view.attr("data-no-wrap") || options.noWrap || !hasMultipleSlides, uniqueNamespace = view.attr("data-namespace") || namespace + i;
                view.attr("data-namespace", uniqueNamespace);
                var setCarouselHeight = function(imageOnly) {
                    var firstSlide = view.find(".carousel-item.active").length ? view.find(".carousel-item.active").first() : view.find(".carousel-item").first(), firstImage = firstSlide.find("img").first();
                    if (firstImage.length) if (firstImage[0].complete) if (0 < firstImage.height()) view.css("height", firstImage.height()); else {
                        var naturalWidth = firstImage[0].naturalWidth, naturalHeight = firstImage[0].naturalHeight, adjustedHeight = view.width() / naturalWidth * naturalHeight;
                        view.css("height", adjustedHeight);
                    } else firstImage.on("load", function() {
                        view.css("height", $(this).height());
                    }); else if (!imageOnly) {
                        var slideHeight = firstSlide.height();
                        view.css("height", slideHeight);
                    }
                };
                if (options.fullWidth && (options.dist = 0, setCarouselHeight(), showIndicators && view.find(".carousel-fixed-item").addClass("with-indicators")), 
                view.hasClass("initialized")) return $(window).trigger("resize"), view.trigger("carouselNext", [ 1e-6 ]), 
                !0;
                function xpos(e) {
                    return e.targetTouches && 1 <= e.targetTouches.length ? e.targetTouches[0].clientX : e.clientX;
                }
                function ypos(e) {
                    return e.targetTouches && 1 <= e.targetTouches.length ? e.targetTouches[0].clientY : e.clientY;
                }
                function wrap(x) {
                    return count <= x ? x % count : x < 0 ? wrap(count + x % count) : x;
                }
                function scroll(x) {
                    var i, half, delta, dir, tween, el, alignment;
                    !0, view.hasClass("scrolling") || view.addClass("scrolling"), null != scrollingTimeout && window.clearTimeout(scrollingTimeout), 
                    scrollingTimeout = window.setTimeout(function() {
                        !1, view.removeClass("scrolling");
                    }, options.duration);
                    var lastCenter = center;
                    if (offset = "number" == typeof x ? x : offset, center = Math.floor((offset + dim / 2) / dim), 
                    tween = -(dir = (delta = offset - center * dim) < 0 ? 1 : -1) * delta * 2 / dim, 
                    half = count >> 1, options.fullWidth ? alignment = "translateX(0)" : (alignment = "translateX(" + (view[0].clientWidth - item_width) / 2 + "px) ", 
                    alignment += "translateY(" + (view[0].clientHeight - item_height) / 2 + "px)"), 
                    showIndicators) {
                        var diff = center % count, activeIndicator = $indicators.find(".indicator-item.active");
                        activeIndicator.index() !== diff && (activeIndicator.removeClass("active"), $indicators.find(".indicator-item").eq(diff).addClass("active"));
                    }
                    for ((!noWrap || 0 <= center && center < count) && (el = images[wrap(center)], $(el).hasClass("active") || (view.find(".carousel-item").removeClass("active"), 
                    $(el).addClass("active")), el.style[xform] = alignment + " translateX(" + -delta / 2 + "px) translateX(" + dir * options.shift * tween * i + "px) translateZ(" + options.dist * tween + "px)", 
                    el.style.zIndex = 0, options.fullWidth ? tweenedOpacity = 1 : tweenedOpacity = 1 - .2 * tween, 
                    el.style.opacity = tweenedOpacity, el.style.display = "block"), i = 1; i <= half; ++i) options.fullWidth ? (zTranslation = options.dist, 
                    tweenedOpacity = i === half && delta < 0 ? 1 - tween : 1) : (zTranslation = options.dist * (2 * i + tween * dir), 
                    tweenedOpacity = 1 - .2 * (2 * i + tween * dir)), (!noWrap || center + i < count) && ((el = images[wrap(center + i)]).style[xform] = alignment + " translateX(" + (options.shift + (dim * i - delta) / 2) + "px) translateZ(" + zTranslation + "px)", 
                    el.style.zIndex = -i, el.style.opacity = tweenedOpacity, el.style.display = "block"), 
                    options.fullWidth ? (zTranslation = options.dist, tweenedOpacity = i === half && 0 < delta ? 1 - tween : 1) : (zTranslation = options.dist * (2 * i - tween * dir), 
                    tweenedOpacity = 1 - .2 * (2 * i - tween * dir)), (!noWrap || 0 <= center - i) && ((el = images[wrap(center - i)]).style[xform] = alignment + " translateX(" + (-options.shift + (-dim * i - delta) / 2) + "px) translateZ(" + zTranslation + "px)", 
                    el.style.zIndex = -i, el.style.opacity = tweenedOpacity, el.style.display = "block");
                    if ((!noWrap || 0 <= center && center < count) && ((el = images[wrap(center)]).style[xform] = alignment + " translateX(" + -delta / 2 + "px) translateX(" + dir * options.shift * tween + "px) translateZ(" + options.dist * tween + "px)", 
                    el.style.zIndex = 0, options.fullWidth ? tweenedOpacity = 1 : tweenedOpacity = 1 - .2 * tween, 
                    el.style.opacity = tweenedOpacity, el.style.display = "block"), lastCenter !== center && "function" == typeof options.onCycleTo) {
                        var $curr_item = view.find(".carousel-item").eq(wrap(center));
                        options.onCycleTo.call(this, $curr_item, dragged);
                    }
                    "function" == typeof oneTimeCallback && (oneTimeCallback.call(this, $curr_item, dragged), 
                    oneTimeCallback = null);
                }
                function track() {
                    var now, elapsed, delta;
                    elapsed = (now = Date.now()) - timestamp, timestamp = now, delta = offset - frame, 
                    frame = offset, velocity = .8 * (1e3 * delta / (1 + elapsed)) + .2 * velocity;
                }
                function autoScroll() {
                    var elapsed, delta;
                    amplitude && (elapsed = Date.now() - timestamp, 2 < (delta = amplitude * Math.exp(-elapsed / options.duration)) || delta < -2 ? (scroll(target - delta), 
                    requestAnimationFrame(autoScroll)) : scroll(target));
                }
                function click(e) {
                    if (dragged) return e.preventDefault(), e.stopPropagation(), !1;
                    if (!options.fullWidth) {
                        var clickedIndex = $(e.target).closest(".carousel-item").index();
                        0 !== wrap(center) - clickedIndex && (e.preventDefault(), e.stopPropagation()), 
                        cycleTo(clickedIndex);
                    }
                }
                function cycleTo(n) {
                    var diff = center % count - n;
                    noWrap || (diff < 0 ? Math.abs(diff + count) < Math.abs(diff) && (diff += count) : 0 < diff && Math.abs(diff - count) < diff && (diff -= count)), 
                    diff < 0 ? view.trigger("carouselNext", [ Math.abs(diff) ]) : 0 < diff && view.trigger("carouselPrev", [ diff ]);
                }
                function tap(e) {
                    "mousedown" === e.type && $(e.target).is("img") && e.preventDefault(), vertical_dragged = dragged = !(pressed = !0), 
                    reference = xpos(e), referenceY = ypos(e), velocity = amplitude = 0, frame = offset, 
                    timestamp = Date.now(), clearInterval(ticker), ticker = setInterval(track, 100);
                }
                function drag(e) {
                    var x, delta;
                    if (pressed) if (x = xpos(e), y = ypos(e), delta = reference - x, Math.abs(referenceY - y) < 30 && !vertical_dragged) (2 < delta || delta < -2) && (dragged = !0, 
                    reference = x, scroll(offset + delta)); else {
                        if (dragged) return e.preventDefault(), e.stopPropagation(), !1;
                        vertical_dragged = !0;
                    }
                    if (dragged) return e.preventDefault(), e.stopPropagation(), !1;
                }
                function release(e) {
                    if (pressed) return pressed = !1, clearInterval(ticker), target = offset, (10 < velocity || velocity < -10) && (target = offset + (amplitude = .9 * velocity)), 
                    target = Math.round(target / dim) * dim, noWrap && (dim * (count - 1) <= target ? target = dim * (count - 1) : target < 0 && (target = 0)), 
                    amplitude = target - offset, timestamp = Date.now(), requestAnimationFrame(autoScroll), 
                    dragged && (e.preventDefault(), e.stopPropagation()), !1;
                }
                view.addClass("initialized"), pressed = !1, offset = target = 0, images = [], item_width = view.find(".carousel-item").first().innerWidth(), 
                item_height = view.find(".carousel-item").first().innerHeight(), dim = 2 * item_width + options.padding, 
                view.find(".carousel-item").each(function(i) {
                    if (images.push($(this)[0]), showIndicators) {
                        var $indicator = $('<li class="indicator-item"></li>');
                        0 === i && $indicator.addClass("active"), $indicator.click(function(e) {
                            e.stopPropagation(), cycleTo($(this).index());
                        }), $indicators.append($indicator);
                    }
                }), showIndicators && view.append($indicators), count = images.length, xform = "transform", 
                [ "webkit", "Moz", "O", "ms" ].every(function(prefix) {
                    var e = prefix + "Transform";
                    return void 0 === document.body.style[e] || (xform = e, !1);
                });
                var throttledResize = Materialize.throttle(function() {
                    if (options.fullWidth) {
                        item_width = view.find(".carousel-item").first().innerWidth();
                        view.find(".carousel-item.active").height();
                        dim = 2 * item_width + options.padding, target = offset = 2 * center * item_width, 
                        setCarouselHeight(!0);
                    } else scroll();
                }, 200);
                $(window).off("resize.carousel-" + uniqueNamespace).on("resize.carousel-" + uniqueNamespace, throttledResize), 
                void 0 !== window.ontouchstart && (view.on("touchstart.carousel", tap), view.on("touchmove.carousel", drag), 
                view.on("touchend.carousel", release)), view.on("mousedown.carousel", tap), view.on("mousemove.carousel", drag), 
                view.on("mouseup.carousel", release), view.on("mouseleave.carousel", release), view.on("click.carousel", click), 
                scroll(offset), $(this).on("carouselNext", function(e, n, callback) {
                    void 0 === n && (n = 1), "function" == typeof callback && (oneTimeCallback = callback), 
                    target = dim * Math.round(offset / dim) + dim * n, offset !== target && (amplitude = target - offset, 
                    timestamp = Date.now(), requestAnimationFrame(autoScroll));
                }), $(this).on("carouselPrev", function(e, n, callback) {
                    void 0 === n && (n = 1), "function" == typeof callback && (oneTimeCallback = callback), 
                    target = dim * Math.round(offset / dim) - dim * n, offset !== target && (amplitude = target - offset, 
                    timestamp = Date.now(), requestAnimationFrame(autoScroll));
                }), $(this).on("carouselSet", function(e, n, callback) {
                    void 0 === n && (n = 0), "function" == typeof callback && (oneTimeCallback = callback), 
                    cycleTo(n);
                });
            });
        },
        next: function(n, callback) {
            $(this).trigger("carouselNext", [ n, callback ]);
        },
        prev: function(n, callback) {
            $(this).trigger("carouselPrev", [ n, callback ]);
        },
        set: function(n, callback) {
            $(this).trigger("carouselSet", [ n, callback ]);
        },
        destroy: function() {
            var uniqueNamespace = $(this).attr("data-namespace");
            $(this).removeAttr("data-namespace"), $(this).removeClass("initialized"), $(this).find(".indicators").remove(), 
            $(this).off("carouselNext carouselPrev carouselSet"), $(window).off("resize.carousel-" + uniqueNamespace), 
            void 0 !== window.ontouchstart && $(this).off("touchstart.carousel touchmove.carousel touchend.carousel"), 
            $(this).off("mousedown.carousel mousemove.carousel mouseup.carousel mouseleave.carousel click.carousel");
        }
    };
    $.fn.carousel = function(methodOrOptions) {
        return methods[methodOrOptions] ? methods[methodOrOptions].apply(this, Array.prototype.slice.call(arguments, 1)) : "object" != typeof methodOrOptions && methodOrOptions ? void $.error("Method " + methodOrOptions + " does not exist on jQuery.carousel") : methods.init.apply(this, arguments);
    };
}(jQuery), function($) {
    function updateCounter() {
        var maxLength = +$(this).attr("data-length"), actualLength = +$(this).val().length, isValidLength = actualLength <= maxLength;
        $(this).parent().find('span[class="character-counter"]').html(actualLength + "/" + maxLength), 
        function(isValidLength, $input) {
            var inputHasInvalidClass = $input.hasClass("invalid");
            isValidLength && inputHasInvalidClass ? $input.removeClass("invalid") : isValidLength || inputHasInvalidClass || ($input.removeClass("valid"), 
            $input.addClass("invalid"));
        }(isValidLength, $(this));
    }
    function removeCounterElement() {
        $(this).parent().find('span[class="character-counter"]').html("");
    }
    $.fn.characterCounter = function() {
        return this.each(function() {
            var $input = $(this);
            $input.parent().find('span[class="character-counter"]').length || void 0 !== $input.attr("data-length") && ($input.on("input", updateCounter), 
            $input.on("focus", updateCounter), $input.on("blur", removeCounterElement), function($input) {
                var $counterElement = $input.parent().find('span[class="character-counter"]');
                if ($counterElement.length) return;
                $counterElement = $("<span/>").addClass("character-counter").css("float", "right").css("font-size", "12px").css("height", 1), 
                $input.parent().append($counterElement);
            }($input));
        });
    }, $(document).ready(function() {
        $("input, textarea").characterCounter();
    });
}(jQuery), function($) {
    var materialChipsDefaults = {
        data: [],
        placeholder: "",
        secondaryPlaceholder: "",
        autocompleteOptions: {}
    };
    $(document).ready(function() {
        $(document).on("click", ".chip .close", function(e) {
            $(this).closest(".chips").attr("data-initialized") || $(this).closest(".chip").remove();
        });
    }), $.fn.material_chip = function(options) {
        var self = this;
        if (this.$el = $(this), this.$document = $(document), this.SELS = {
            CHIPS: ".chips",
            CHIP: ".chip",
            INPUT: "input",
            DELETE: ".material-icons",
            SELECTED_CHIP: ".selected"
        }, "data" === options) return this.$el.data("chips");
        var curr_options = $.extend({}, materialChipsDefaults, options);
        self.hasAutocomplete = !$.isEmptyObject(curr_options.autocompleteOptions.data), 
        this.init = function() {
            var i = 0;
            self.$el.each(function() {
                var $chips = $(this), chipId = Materialize.guid();
                self.chipId = chipId, curr_options.data && curr_options.data instanceof Array || (curr_options.data = []), 
                $chips.data("chips", curr_options.data), $chips.attr("data-index", i), $chips.attr("data-initialized", !0), 
                $chips.hasClass(self.SELS.CHIPS) || $chips.addClass("chips"), self.chips($chips, chipId), 
                i++;
            });
        }, this.handleEvents = function() {
            var SELS = self.SELS;
            self.$document.off("click.chips-focus", SELS.CHIPS).on("click.chips-focus", SELS.CHIPS, function(e) {
                $(e.target).find(SELS.INPUT).focus();
            }), self.$document.off("click.chips-select", SELS.CHIP).on("click.chips-select", SELS.CHIP, function(e) {
                var $chip = $(e.target);
                if ($chip.length) {
                    var wasSelected = $chip.hasClass("selected"), $chips = $chip.closest(SELS.CHIPS);
                    $(SELS.CHIP).removeClass("selected"), wasSelected || self.selectChip($chip.index(), $chips);
                }
            }), self.$document.off("keydown.chips").on("keydown.chips", function(e) {
                if (!$(e.target).is("input, textarea")) {
                    var index, $chip = self.$document.find(SELS.CHIP + SELS.SELECTED_CHIP), $chips = $chip.closest(SELS.CHIPS), length = $chip.siblings(SELS.CHIP).length;
                    if ($chip.length) if (8 === e.which || 46 === e.which) {
                        e.preventDefault(), index = $chip.index(), self.deleteChip(index, $chips);
                        var selectIndex = null;
                        index + 1 < length ? selectIndex = index : index !== length && index + 1 !== length || (selectIndex = length - 1), 
                        selectIndex < 0 && (selectIndex = null), null !== selectIndex && self.selectChip(selectIndex, $chips), 
                        length || $chips.find("input").focus();
                    } else if (37 === e.which) {
                        if ((index = $chip.index() - 1) < 0) return;
                        $(SELS.CHIP).removeClass("selected"), self.selectChip(index, $chips);
                    } else if (39 === e.which) {
                        if (index = $chip.index() + 1, $(SELS.CHIP).removeClass("selected"), length < index) return void $chips.find("input").focus();
                        self.selectChip(index, $chips);
                    }
                }
            }), self.$document.off("focusin.chips", SELS.CHIPS + " " + SELS.INPUT).on("focusin.chips", SELS.CHIPS + " " + SELS.INPUT, function(e) {
                var $currChips = $(e.target).closest(SELS.CHIPS);
                $currChips.addClass("focus"), $currChips.siblings("label, .prefix").addClass("active"), 
                $(SELS.CHIP).removeClass("selected");
            }), self.$document.off("focusout.chips", SELS.CHIPS + " " + SELS.INPUT).on("focusout.chips", SELS.CHIPS + " " + SELS.INPUT, function(e) {
                var $currChips = $(e.target).closest(SELS.CHIPS);
                $currChips.removeClass("focus"), void 0 !== $currChips.data("chips") && $currChips.data("chips").length || $currChips.siblings("label").removeClass("active"), 
                $currChips.siblings(".prefix").removeClass("active");
            }), self.$document.off("keydown.chips-add", SELS.CHIPS + " " + SELS.INPUT).on("keydown.chips-add", SELS.CHIPS + " " + SELS.INPUT, function(e) {
                var $target = $(e.target), $chips = $target.closest(SELS.CHIPS), chipsLength = $chips.children(SELS.CHIP).length;
                if (13 === e.which) {
                    if (self.hasAutocomplete && $chips.find(".autocomplete-content.dropdown-content").length && $chips.find(".autocomplete-content.dropdown-content").children().length) return;
                    return e.preventDefault(), self.addChip({
                        tag: $target.val()
                    }, $chips), void $target.val("");
                }
                if ((8 === e.keyCode || 37 === e.keyCode) && "" === $target.val() && chipsLength) return e.preventDefault(), 
                self.selectChip(chipsLength - 1, $chips), void $target.blur();
            }), self.$document.off("click.chips-delete", SELS.CHIPS + " " + SELS.DELETE).on("click.chips-delete", SELS.CHIPS + " " + SELS.DELETE, function(e) {
                var $target = $(e.target), $chips = $target.closest(SELS.CHIPS), $chip = $target.closest(SELS.CHIP);
                e.stopPropagation(), self.deleteChip($chip.index(), $chips), $chips.find("input").focus();
            });
        }, this.chips = function($chips, chipId) {
            $chips.empty(), $chips.data("chips").forEach(function(elem) {
                $chips.append(self.renderChip(elem));
            }), $chips.append($('<input id="' + chipId + '" class="input" placeholder="">')), 
            self.setPlaceholder($chips);
            var label = $chips.next("label");
            label.length && (label.attr("for", chipId), void 0 !== $chips.data("chips") && $chips.data("chips").length && label.addClass("active"));
            var input = $("#" + chipId);
            self.hasAutocomplete && (curr_options.autocompleteOptions.onAutocomplete = function(val) {
                self.addChip({
                    tag: val
                }, $chips), input.val(""), input.focus();
            }, input.autocomplete(curr_options.autocompleteOptions));
        }, this.renderChip = function(elem) {
            if (elem.tag) {
                var $renderedChip = $('<div class="chip"></div>');
                return $renderedChip.text(elem.tag), elem.image && $renderedChip.prepend($("<img />").attr("src", elem.image)), 
                $renderedChip.append($('<i class="material-icons close">close</i>')), $renderedChip;
            }
        }, this.setPlaceholder = function($chips) {
            void 0 !== $chips.data("chips") && !$chips.data("chips").length && curr_options.placeholder ? $chips.find("input").prop("placeholder", curr_options.placeholder) : (void 0 === $chips.data("chips") || $chips.data("chips").length) && curr_options.secondaryPlaceholder && $chips.find("input").prop("placeholder", curr_options.secondaryPlaceholder);
        }, this.isValid = function($chips, elem) {
            for (var chips = $chips.data("chips"), exists = !1, i = 0; i < chips.length; i++) if (chips[i].tag === elem.tag) return void (exists = !0);
            return "" !== elem.tag && !exists;
        }, this.addChip = function(elem, $chips) {
            if (self.isValid($chips, elem)) {
                for (var $renderedChip = self.renderChip(elem), newData = [], oldData = $chips.data("chips"), i = 0; i < oldData.length; i++) newData.push(oldData[i]);
                newData.push(elem), $chips.data("chips", newData), $renderedChip.insertBefore($chips.find("input")), 
                $chips.trigger("chip.add", elem), self.setPlaceholder($chips);
            }
        }, this.deleteChip = function(chipIndex, $chips) {
            var chip = $chips.data("chips")[chipIndex];
            $chips.find(".chip").eq(chipIndex).remove();
            for (var newData = [], oldData = $chips.data("chips"), i = 0; i < oldData.length; i++) i !== chipIndex && newData.push(oldData[i]);
            $chips.data("chips", newData), $chips.trigger("chip.delete", chip), self.setPlaceholder($chips);
        }, this.selectChip = function(chipIndex, $chips) {
            var $chip = $chips.find(".chip").eq(chipIndex);
            $chip && !1 === $chip.hasClass("selected") && ($chip.addClass("selected"), $chips.trigger("chip.select", $chips.data("chips")[chipIndex]));
        }, this.getChipsElement = function(index, $chips) {
            return $chips.eq(index);
        }, this.init(), this.handleEvents();
    };
}(jQuery), function($) {
    $.fn.collapsible = function(options, methodParam) {
        var defaults = {
            accordion: void 0,
            onOpen: void 0,
            onClose: void 0
        }, methodName = options;
        return options = $.extend(defaults, options), this.each(function() {
            var $this = $(this), $panel_headers = $(this).find("> li > .collapsible-header"), collapsible_type = $this.data("collapsible");
            function collapsibleOpen(object, noToggle) {
                noToggle || object.toggleClass("active"), options.accordion || "accordion" === collapsible_type || void 0 === collapsible_type ? function(object) {
                    $panel_headers = $this.find("> li > .collapsible-header"), object.hasClass("active") ? object.parent().addClass("active") : object.parent().removeClass("active"), 
                    object.parent().hasClass("active") ? object.siblings(".collapsible-body").stop(!0, !1).slideDown({
                        duration: 350,
                        easing: "easeOutQuart",
                        queue: !1,
                        complete: function() {
                            $(this).css("height", "");
                        }
                    }) : object.siblings(".collapsible-body").stop(!0, !1).slideUp({
                        duration: 350,
                        easing: "easeOutQuart",
                        queue: !1,
                        complete: function() {
                            $(this).css("height", "");
                        }
                    }), $panel_headers.not(object).removeClass("active").parent().removeClass("active"), 
                    $panel_headers.not(object).parent().children(".collapsible-body").stop(!0, !1).each(function() {
                        $(this).is(":visible") && $(this).slideUp({
                            duration: 350,
                            easing: "easeOutQuart",
                            queue: !1,
                            complete: function() {
                                $(this).css("height", ""), execCallbacks($(this).siblings(".collapsible-header"));
                            }
                        });
                    });
                }(object) : function(object) {
                    object.hasClass("active") ? object.parent().addClass("active") : object.parent().removeClass("active"), 
                    object.parent().hasClass("active") ? object.siblings(".collapsible-body").stop(!0, !1).slideDown({
                        duration: 350,
                        easing: "easeOutQuart",
                        queue: !1,
                        complete: function() {
                            $(this).css("height", "");
                        }
                    }) : object.siblings(".collapsible-body").stop(!0, !1).slideUp({
                        duration: 350,
                        easing: "easeOutQuart",
                        queue: !1,
                        complete: function() {
                            $(this).css("height", "");
                        }
                    });
                }(object), execCallbacks(object);
            }
            function execCallbacks(object) {
                object.hasClass("active") ? "function" == typeof options.onOpen && options.onOpen.call(this, object.parent()) : "function" == typeof options.onClose && options.onClose.call(this, object.parent());
            }
            function getPanelHeader(object) {
                return object.closest("li > .collapsible-header");
            }
            function removeEventHandlers() {
                $this.off("click.collapse", "> li > .collapsible-header");
            }
            if ("destroy" !== methodName) if (0 <= methodParam && methodParam < $panel_headers.length) {
                var $curr_header = $panel_headers.eq(methodParam);
                $curr_header.length && ("open" === methodName || "close" === methodName && $curr_header.hasClass("active")) && collapsibleOpen($curr_header);
            } else removeEventHandlers(), $this.on("click.collapse", "> li > .collapsible-header", function(e) {
                var element = $(e.target);
                0 < getPanelHeader(element).length && (element = getPanelHeader(element)), collapsibleOpen(element);
            }), options.accordion || "accordion" === collapsible_type || void 0 === collapsible_type ? collapsibleOpen($panel_headers.filter(".active").first(), !0) : $panel_headers.filter(".active").each(function() {
                collapsibleOpen($(this), !0);
            }); else removeEventHandlers();
        });
    }, $(document).ready(function() {
        $(".collapsible").collapsible();
    });
}(jQuery), function($) {
    $.fn.scrollTo = function(elem) {
        return $(this).scrollTop($(this).scrollTop() - $(this).offset().top + $(elem).offset().top), 
        this;
    }, $.fn.dropdown = function(options) {
        var defaults = {
            inDuration: 300,
            outDuration: 225,
            constrainWidth: !0,
            hover: !1,
            gutter: 0,
            belowOrigin: !1,
            alignment: "left",
            stopPropagation: !1
        };
        return "open" === options ? (this.each(function() {
            $(this).trigger("open");
        }), !1) : "close" === options ? (this.each(function() {
            $(this).trigger("close");
        }), !1) : void this.each(function() {
            var origin = $(this), curr_options = $.extend({}, defaults, options), isFocused = !1, activates = $("#" + origin.attr("data-activates"));
            function updateOptions() {
                void 0 !== origin.data("induration") && (curr_options.inDuration = origin.data("induration")), 
                void 0 !== origin.data("outduration") && (curr_options.outDuration = origin.data("outduration")), 
                void 0 !== origin.data("constrainwidth") && (curr_options.constrainWidth = origin.data("constrainwidth")), 
                void 0 !== origin.data("hover") && (curr_options.hover = origin.data("hover")), 
                void 0 !== origin.data("gutter") && (curr_options.gutter = origin.data("gutter")), 
                void 0 !== origin.data("beloworigin") && (curr_options.belowOrigin = origin.data("beloworigin")), 
                void 0 !== origin.data("alignment") && (curr_options.alignment = origin.data("alignment")), 
                void 0 !== origin.data("stoppropagation") && (curr_options.stopPropagation = origin.data("stoppropagation"));
            }
            function placeDropdown(eventType) {
                "focus" === eventType && (isFocused = !0), updateOptions(), activates.addClass("active"), 
                origin.addClass("active");
                var originWidth = origin[0].getBoundingClientRect().width;
                !0 === curr_options.constrainWidth ? activates.css("width", originWidth) : activates.css("white-space", "nowrap");
                var windowHeight = window.innerHeight, originHeight = origin.innerHeight(), offsetLeft = origin.offset().left, offsetTop = origin.offset().top - $(window).scrollTop(), currAlignment = curr_options.alignment, gutterSpacing = 0, leftPosition = 0, verticalOffset = 0;
                !0 === curr_options.belowOrigin && (verticalOffset = originHeight);
                var scrollYOffset = 0, scrollXOffset = 0, wrapper = origin.parent();
                if (wrapper.is("body") || (wrapper[0].scrollHeight > wrapper[0].clientHeight && (scrollYOffset = wrapper[0].scrollTop), 
                wrapper[0].scrollWidth > wrapper[0].clientWidth && (scrollXOffset = wrapper[0].scrollLeft)), 
                offsetLeft + activates.innerWidth() > $(window).width() ? currAlignment = "right" : offsetLeft - activates.innerWidth() + origin.innerWidth() < 0 && (currAlignment = "left"), 
                offsetTop + activates.innerHeight() > windowHeight) if (offsetTop + originHeight - activates.innerHeight() < 0) {
                    var adjustedHeight = windowHeight - offsetTop - verticalOffset;
                    activates.css("max-height", adjustedHeight);
                } else verticalOffset || (verticalOffset += originHeight), verticalOffset -= activates.innerHeight();
                if ("left" === currAlignment) gutterSpacing = curr_options.gutter, leftPosition = origin.position().left + gutterSpacing; else if ("right" === currAlignment) {
                    activates.stop(!0, !0).css({
                        opacity: 0,
                        left: 0
                    }), leftPosition = origin.position().left + originWidth - activates.width() + (gutterSpacing = -curr_options.gutter);
                }
                activates.css({
                    position: "absolute",
                    top: origin.position().top + verticalOffset + scrollYOffset,
                    left: leftPosition + scrollXOffset
                }), activates.slideDown({
                    queue: !1,
                    duration: curr_options.inDuration,
                    easing: "easeOutCubic",
                    complete: function() {
                        $(this).css("height", "");
                    }
                }).animate({
                    opacity: 1
                }, {
                    queue: !1,
                    duration: curr_options.inDuration,
                    easing: "easeOutSine"
                }), setTimeout(function() {
                    $(document).on("click." + activates.attr("id"), function(e) {
                        hideDropdown(), $(document).off("click." + activates.attr("id"));
                    });
                }, 0);
            }
            function hideDropdown() {
                isFocused = !1, activates.fadeOut(curr_options.outDuration), activates.removeClass("active"), 
                origin.removeClass("active"), $(document).off("click." + activates.attr("id")), 
                setTimeout(function() {
                    activates.css("max-height", "");
                }, curr_options.outDuration);
            }
            if (updateOptions(), origin.after(activates), curr_options.hover) {
                var open = !1;
                origin.off("click." + origin.attr("id")), origin.on("mouseenter", function(e) {
                    !1 === open && (placeDropdown(), open = !0);
                }), origin.on("mouseleave", function(e) {
                    var toEl = e.toElement || e.relatedTarget;
                    $(toEl).closest(".dropdown-content").is(activates) || (activates.stop(!0, !0), hideDropdown(), 
                    open = !1);
                }), activates.on("mouseleave", function(e) {
                    var toEl = e.toElement || e.relatedTarget;
                    $(toEl).closest(".dropdown-button").is(origin) || (activates.stop(!0, !0), hideDropdown(), 
                    open = !1);
                });
            } else origin.off("click." + origin.attr("id")), origin.on("click." + origin.attr("id"), function(e) {
                isFocused || (origin[0] != e.currentTarget || origin.hasClass("active") || 0 !== $(e.target).closest(".dropdown-content").length ? origin.hasClass("active") && (hideDropdown(), 
                $(document).off("click." + activates.attr("id"))) : (e.preventDefault(), curr_options.stopPropagation && e.stopPropagation(), 
                placeDropdown("click")));
            });
            origin.on("open", function(e, eventType) {
                placeDropdown(eventType);
            }), origin.on("close", hideDropdown);
        });
    }, $(document).ready(function() {
        $(".dropdown-button").dropdown();
    });
}(jQuery), function($) {
    $(document).ready(function() {
        Materialize.updateTextFields = function() {
            $("input[type=text], input[type=password], input[type=email], input[type=url], input[type=tel], input[type=number], input[type=search], textarea").each(function(index, element) {
                var $this = $(this);
                0 < $(element).val().length || $(element).is(":focus") || element.autofocus || void 0 !== $this.attr("placeholder") ? $this.siblings("label").addClass("active") : $(element)[0].validity ? $this.siblings("label").toggleClass("active", !0 === $(element)[0].validity.badInput) : $this.siblings("label").removeClass("active");
            });
        };
        var input_selector = "input[type=text], input[type=password], input[type=email], input[type=url], input[type=tel], input[type=number], input[type=search], textarea";
        $(document).on("change", input_selector, function() {
            0 === $(this).val().length && void 0 === $(this).attr("placeholder") || $(this).siblings("label").addClass("active"), 
            validate_field($(this));
        }), $(document).ready(function() {
            Materialize.updateTextFields();
        }), $(document).on("reset", function(e) {
            var formReset = $(e.target);
            formReset.is("form") && (formReset.find(input_selector).removeClass("valid").removeClass("invalid"), 
            formReset.find(input_selector).each(function() {
                "" === $(this).attr("value") && $(this).siblings("label").removeClass("active");
            }), formReset.find("select.initialized").each(function() {
                var reset_text = formReset.find("option[selected]").text();
                formReset.siblings("input.select-dropdown").val(reset_text);
            }));
        }), $(document).on("focus", input_selector, function() {
            $(this).siblings("label, .prefix").addClass("active");
        }), $(document).on("blur", input_selector, function() {
            var $inputElement = $(this), selector = ".prefix";
            0 === $inputElement.val().length && !0 !== $inputElement[0].validity.badInput && void 0 === $inputElement.attr("placeholder") && (selector += ", label"), 
            $inputElement.siblings(selector).removeClass("active"), validate_field($inputElement);
        }), window.validate_field = function(object) {
            var hasLength = void 0 !== object.attr("data-length"), lenAttr = parseInt(object.attr("data-length")), len = object.val().length;
            0 !== object.val().length || !1 !== object[0].validity.badInput || object.is(":required") ? object.hasClass("validate") && (object.is(":valid") && hasLength && len <= lenAttr || object.is(":valid") && !hasLength ? (object.removeClass("invalid"), 
            object.addClass("valid")) : (object.removeClass("valid"), object.addClass("invalid"))) : object.hasClass("validate") && (object.removeClass("valid"), 
            object.removeClass("invalid"));
        };
        $(document).on("keyup.radio", "input[type=radio], input[type=checkbox]", function(e) {
            if (9 === e.which) return $(this).addClass("tabbed"), void $(this).one("blur", function(e) {
                $(this).removeClass("tabbed");
            });
        });
        var hiddenDiv = $(".hiddendiv").first();
        hiddenDiv.length || (hiddenDiv = $('<div class="hiddendiv common"></div>'), $("body").append(hiddenDiv));
        $(".materialize-textarea").each(function() {
            var $textarea = $(this);
            $textarea.data("original-height", $textarea.height()), $textarea.data("previous-length", $textarea.val().length);
        }), $("body").on("keyup keydown autoresize", ".materialize-textarea", function() {
            !function($textarea) {
                var fontFamily = $textarea.css("font-family"), fontSize = $textarea.css("font-size"), lineHeight = $textarea.css("line-height"), padding = $textarea.css("padding");
                fontSize && hiddenDiv.css("font-size", fontSize), fontFamily && hiddenDiv.css("font-family", fontFamily), 
                lineHeight && hiddenDiv.css("line-height", lineHeight), padding && hiddenDiv.css("padding", padding), 
                $textarea.data("original-height") || $textarea.data("original-height", $textarea.height()), 
                "off" === $textarea.attr("wrap") && hiddenDiv.css("overflow-wrap", "normal").css("white-space", "pre"), 
                hiddenDiv.text($textarea.val() + "\n");
                var content = hiddenDiv.html().replace(/\n/g, "<br>");
                hiddenDiv.html(content), $textarea.is(":visible") ? hiddenDiv.css("width", $textarea.width()) : hiddenDiv.css("width", $(window).width() / 2), 
                $textarea.data("original-height") <= hiddenDiv.height() ? $textarea.css("height", hiddenDiv.height()) : $textarea.val().length < $textarea.data("previous-length") && $textarea.css("height", $textarea.data("original-height")), 
                $textarea.data("previous-length", $textarea.val().length);
            }($(this));
        }), $(document).on("change", '.file-field input[type="file"]', function() {
            for (var path_input = $(this).closest(".file-field").find("input.file-path"), files = $(this)[0].files, file_names = [], i = 0; i < files.length; i++) file_names.push(files[i].name);
            path_input.val(file_names.join(", ")), path_input.trigger("change");
        });
        var range_type = "input[type=range]", range_mousedown = !1;
        $(range_type).each(function() {
            var thumb = $('<span class="thumb"><span class="value"></span></span>');
            $(this).after(thumb);
        });
        var showRangeBubble = function(thumb) {
            var marginLeft = -7 + parseInt(thumb.parent().css("padding-left")) + "px";
            thumb.velocity({
                height: "30px",
                width: "30px",
                top: "-30px",
                marginLeft: marginLeft
            }, {
                duration: 300,
                easing: "easeOutExpo"
            });
        }, calcRangeOffset = function(range) {
            var width = range.width() - 15, max = parseFloat(range.attr("max")), min = parseFloat(range.attr("min"));
            return (parseFloat(range.val()) - min) / (max - min) * width;
        };
        $(document).on("change", range_type, function(e) {
            var thumb = $(this).siblings(".thumb");
            thumb.find(".value").html($(this).val()), thumb.hasClass("active") || showRangeBubble(thumb);
            var offsetLeft = calcRangeOffset($(this));
            thumb.addClass("active").css("left", offsetLeft);
        }), $(document).on("mousedown touchstart", range_type, function(e) {
            var thumb = $(this).siblings(".thumb");
            if (thumb.length <= 0 && (thumb = $('<span class="thumb"><span class="value"></span></span>'), 
            $(this).after(thumb)), thumb.find(".value").html($(this).val()), range_mousedown = !0, 
            $(this).addClass("active"), thumb.hasClass("active") || showRangeBubble(thumb), 
            "input" !== e.type) {
                var offsetLeft = calcRangeOffset($(this));
                thumb.addClass("active").css("left", offsetLeft);
            }
        }), $(document).on("mouseup touchend", ".range-field", function() {
            range_mousedown = !1, $(this).removeClass("active");
        }), $(document).on("input mousemove touchmove", ".range-field", function(e) {
            var thumb = $(this).children(".thumb"), input = $(this).find(range_type);
            if (range_mousedown) {
                thumb.hasClass("active") || showRangeBubble(thumb);
                var offsetLeft = calcRangeOffset(input);
                thumb.addClass("active").css("left", offsetLeft), thumb.find(".value").html(thumb.siblings(range_type).val());
            }
        }), $(document).on("mouseout touchleave", ".range-field", function() {
            if (!range_mousedown) {
                var thumb = $(this).children(".thumb"), marginLeft = 7 + parseInt($(this).css("padding-left")) + "px";
                thumb.hasClass("active") && thumb.velocity({
                    height: "0",
                    width: "0",
                    top: "10px",
                    marginLeft: marginLeft
                }, {
                    duration: 100
                }), thumb.removeClass("active");
            }
        }), $.fn.autocomplete = function(options) {
            var defaults = {
                data: {},
                limit: 1 / 0,
                onAutocomplete: null,
                minLength: 1
            };
            return options = $.extend(defaults, options), this.each(function() {
                var oldVal, $input = $(this), data = options.data, count = 0, activeIndex = -1, $inputDiv = $input.closest(".input-field");
                if ($.isEmptyObject(data)) $input.off("keyup.autocomplete focus.autocomplete"); else {
                    var $oldAutocomplete, $autocomplete = $('<ul class="autocomplete-content dropdown-content"></ul>');
                    $inputDiv.length ? ($oldAutocomplete = $inputDiv.children(".autocomplete-content.dropdown-content").first()).length || $inputDiv.append($autocomplete) : ($oldAutocomplete = $input.next(".autocomplete-content.dropdown-content")).length || $input.after($autocomplete), 
                    $oldAutocomplete.length && ($autocomplete = $oldAutocomplete);
                    var removeAutocomplete = function() {
                        $autocomplete.empty(), activeIndex = -1, $autocomplete.find(".active").removeClass("active"), 
                        oldVal = void 0;
                    };
                    $input.off("blur.autocomplete").on("blur.autocomplete", function() {
                        removeAutocomplete();
                    }), $input.off("keyup.autocomplete focus.autocomplete").on("keyup.autocomplete focus.autocomplete", function(e) {
                        count = 0;
                        var val = $input.val().toLowerCase();
                        if (13 !== e.which && 38 !== e.which && 40 !== e.which) {
                            if (oldVal !== val && (removeAutocomplete(), val.length >= options.minLength)) for (var key in data) if (data.hasOwnProperty(key) && -1 !== key.toLowerCase().indexOf(val)) {
                                if (count >= options.limit) break;
                                var autocompleteOption = $("<li></li>");
                                data[key] ? autocompleteOption.append('<img src="' + data[key] + '" class="right circle"><span>' + key + "</span>") : autocompleteOption.append("<span>" + key + "</span>"), 
                                $autocomplete.append(autocompleteOption), string = val, void 0, img = ($el = autocompleteOption).find("img"), 
                                matchStart = $el.text().toLowerCase().indexOf("" + string.toLowerCase()), matchEnd = matchStart + string.length - 1, 
                                beforeMatch = $el.text().slice(0, matchStart), matchText = $el.text().slice(matchStart, matchEnd + 1), 
                                afterMatch = $el.text().slice(matchEnd + 1), $el.html("<span>" + beforeMatch + "<span class='highlight'>" + matchText + "</span>" + afterMatch + "</span>"), 
                                img.length && $el.prepend(img), count++;
                            }
                            var string, $el, img, matchStart, matchEnd, beforeMatch, matchText, afterMatch;
                            oldVal = val;
                        }
                    }), $input.off("keydown.autocomplete").on("keydown.autocomplete", function(e) {
                        var liElement, keyCode = e.which, numItems = $autocomplete.children("li").length, $active = $autocomplete.children(".active").first();
                        13 === keyCode && 0 <= activeIndex ? (liElement = $autocomplete.children("li").eq(activeIndex)).length && (liElement.trigger("mousedown.autocomplete"), 
                        e.preventDefault()) : 38 !== keyCode && 40 !== keyCode || (e.preventDefault(), 38 === keyCode && 0 < activeIndex && activeIndex--, 
                        40 === keyCode && activeIndex < numItems - 1 && activeIndex++, $active.removeClass("active"), 
                        0 <= activeIndex && $autocomplete.children("li").eq(activeIndex).addClass("active"));
                    }), $autocomplete.off("mousedown.autocomplete touchstart.autocomplete").on("mousedown.autocomplete touchstart.autocomplete", "li", function() {
                        var text = $(this).text().trim();
                        $input.val(text), $input.trigger("change"), removeAutocomplete(), "function" == typeof options.onAutocomplete && options.onAutocomplete.call(this, text);
                    });
                }
            });
        };
    }), $.fn.material_select = function(callback) {
        function toggleEntryFromArray(entriesArray, entryIndex, select) {
            var index = entriesArray.indexOf(entryIndex), notAdded = -1 === index;
            return notAdded ? entriesArray.push(entryIndex) : entriesArray.splice(index, 1), 
            select.siblings("ul.dropdown-content").find("li:not(.optgroup)").eq(entryIndex).toggleClass("active"), 
            select.find("option").eq(entryIndex).prop("selected", notAdded), function(entriesArray, select) {
                for (var value = "", i = 0, count = entriesArray.length; i < count; i++) {
                    var text = select.find("option").eq(entriesArray[i]).text();
                    value += 0 === i ? text : ", " + text;
                }
                "" === value && (value = select.find("option:disabled").eq(0).text());
                select.siblings("input.select-dropdown").val(value);
            }(entriesArray, select), notAdded;
        }
        $(this).each(function() {
            var $select = $(this);
            if (!$select.hasClass("browser-default")) {
                var multiple = !!$select.attr("multiple"), lastID = $select.attr("data-select-id");
                if (lastID && ($select.parent().find("span.caret").remove(), $select.parent().find("input").remove(), 
                $select.unwrap(), $("ul#select-options-" + lastID).remove()), "destroy" === callback) return $select.removeAttr("data-select-id").removeClass("initialized"), 
                void $(window).off("click.select");
                var uniqueID = Materialize.guid();
                $select.attr("data-select-id", uniqueID);
                var wrapper = $('<div class="select-wrapper"></div>');
                wrapper.addClass($select.attr("class")), $select.is(":disabled") && wrapper.addClass("disabled");
                var options = $('<ul id="select-options-' + uniqueID + '" class="dropdown-content select-dropdown ' + (multiple ? "multiple-select-dropdown" : "") + '"></ul>'), selectChildren = $select.children("option, optgroup"), valuesSelected = [], optionsHover = !1, label = $select.find("option:selected").html() || $select.find("option:first").html() || "", appendOptionWithIcon = function(select, option, type) {
                    var disabledClass = option.is(":disabled") ? "disabled " : "", optgroupClass = "optgroup-option" === type ? "optgroup-option " : "", multipleCheckbox = multiple ? '<input type="checkbox"' + disabledClass + "/><label></label>" : "", icon_url = option.data("icon"), classes = option.attr("class");
                    if (icon_url) {
                        var classString = "";
                        return classes && (classString = ' class="' + classes + '"'), options.append($('<li class="' + disabledClass + optgroupClass + '"><img alt="" src="' + icon_url + '"' + classString + "><span>" + multipleCheckbox + option.html() + "</span></li>")), 
                        !0;
                    }
                    options.append($('<li class="' + disabledClass + optgroupClass + '"><span>' + multipleCheckbox + option.html() + "</span></li>"));
                };
                selectChildren.length && selectChildren.each(function() {
                    if ($(this).is("option")) multiple ? appendOptionWithIcon(0, $(this), "multiple") : appendOptionWithIcon(0, $(this)); else if ($(this).is("optgroup")) {
                        var selectOptions = $(this).children("option");
                        options.append($('<li class="optgroup"><span>' + $(this).attr("label") + "</span></li>")), 
                        selectOptions.each(function() {
                            appendOptionWithIcon(0, $(this), "optgroup-option");
                        });
                    }
                }), options.find("li:not(.optgroup)").each(function(i) {
                    $(this).click(function(e) {
                        if (!$(this).hasClass("disabled") && !$(this).hasClass("optgroup")) {
                            var selected = !0;
                            multiple ? ($('input[type="checkbox"]', this).prop("checked", function(i, v) {
                                return !v;
                            }), selected = toggleEntryFromArray(valuesSelected, i, $select), $newSelect.trigger("focus")) : (options.find("li").removeClass("active"), 
                            $(this).toggleClass("active"), $newSelect.val($(this).text())), activateOption(options, $(this)), 
                            $select.find("option").eq(i).prop("selected", selected), $select.trigger("change"), 
                            void 0 !== callback && callback();
                        }
                        e.stopPropagation();
                    });
                }), $select.wrap(wrapper);
                var dropdownIcon = $('<span class="caret">&#9660;</span>'), sanitizedLabelHtml = label.replace(/"/g, "&quot;"), $newSelect = $('<input type="text" class="select-dropdown" readonly="true" ' + ($select.is(":disabled") ? "disabled" : "") + ' data-activates="select-options-' + uniqueID + '" value="' + sanitizedLabelHtml + '"/>');
                $select.before($newSelect), $newSelect.before(dropdownIcon), $newSelect.after(options), 
                $select.is(":disabled") || $newSelect.dropdown({
                    hover: !1
                }), $select.attr("tabindex") && $($newSelect[0]).attr("tabindex", $select.attr("tabindex")), 
                $select.addClass("initialized"), $newSelect.on({
                    focus: function() {
                        setTimeout(function() {
                            if ($("ul.select-dropdown").not(options[0]).is(":visible") && ($("input.select-dropdown").trigger("close"), 
                            $(window).off("click.select")), !options.is(":visible")) {
                                $(this).trigger("open", [ "focus" ]);
                                var label = $(this).val();
                                multiple && 0 <= label.indexOf(",") && (label = label.split(",")[0]);
                                var selectedOption = options.find("li").filter(function() {
                                    return $(this).text().toLowerCase() === label.toLowerCase();
                                })[0];
                                activateOption(options, selectedOption, !0), $(window).off("click.select").on("click.select", function() {
                                    multiple && (optionsHover || $newSelect.trigger("close")), $(window).off("click.select");
                                });
                            }
                        }, 75);
                    },
                    click: function(e) {
                        e.stopPropagation();
                    }
                }), $newSelect.on("blur", function() {
                    multiple || ($(this).trigger("close"), $(window).off("click.select")), options.find("li.selected").removeClass("selected");
                }), options.hover(function() {
                    optionsHover = !0;
                }, function() {
                    optionsHover = !1;
                }), multiple && $select.find("option:selected:not(:disabled)").each(function() {
                    var index = this.index;
                    toggleEntryFromArray(valuesSelected, index, $select), options.find("li:not(.optgroup)").eq(index).find(":checkbox").prop("checked", !0);
                });
                var activateOption = function(collection, newOption, firstActivation) {
                    if (newOption) {
                        collection.find("li.selected").removeClass("selected");
                        var option = $(newOption);
                        option.addClass("selected"), multiple && !firstActivation || options.scrollTo(option);
                    }
                }, filterQuery = [];
                $newSelect.on("keydown", function(e) {
                    if (9 != e.which) if (40 != e.which || options.is(":visible")) {
                        if (13 != e.which || options.is(":visible")) {
                            e.preventDefault();
                            var letter = String.fromCharCode(e.which).toLowerCase();
                            if (letter && -1 === [ 9, 13, 27, 38, 40 ].indexOf(e.which)) {
                                filterQuery.push(letter);
                                var string = filterQuery.join(""), newOption = options.find("li").filter(function() {
                                    return 0 === $(this).text().toLowerCase().indexOf(string);
                                })[0];
                                newOption && activateOption(options, newOption);
                            }
                            if (13 == e.which) {
                                var activeOption = options.find("li.selected:not(.disabled)")[0];
                                activeOption && ($(activeOption).trigger("click"), multiple || $newSelect.trigger("close"));
                            }
                            40 == e.which && (newOption = options.find("li.selected").length ? options.find("li.selected").next("li:not(.disabled)")[0] : options.find("li:not(.disabled)")[0], 
                            activateOption(options, newOption)), 27 == e.which && $newSelect.trigger("close"), 
                            38 == e.which && (newOption = options.find("li.selected").prev("li:not(.disabled)")[0]) && activateOption(options, newOption), 
                            setTimeout(function() {
                                filterQuery = [];
                            }, 1e3);
                        }
                    } else $newSelect.trigger("open"); else $newSelect.trigger("close");
                });
            }
        });
    };
}(jQuery), function(window) {
    window.Package ? Materialize = {} : window.Materialize = {};
}(window), "undefined" == typeof exports || exports.nodeType || ("undefined" != typeof module && !module.nodeType && module.exports && (exports = module.exports = Materialize), 
exports.default = Materialize), function(window) {
    for (var lastTime = 0, vendors = [ "webkit", "moz" ], requestAnimationFrame = window.requestAnimationFrame, cancelAnimationFrame = window.cancelAnimationFrame, i = vendors.length; 0 <= --i && !requestAnimationFrame; ) requestAnimationFrame = window[vendors[i] + "RequestAnimationFrame"], 
    cancelAnimationFrame = window[vendors[i] + "CancelRequestAnimationFrame"];
    requestAnimationFrame && cancelAnimationFrame || (requestAnimationFrame = function(callback) {
        var now = +Date.now(), nextTime = Math.max(lastTime + 16, now);
        return setTimeout(function() {
            callback(lastTime = nextTime);
        }, nextTime - now);
    }, cancelAnimationFrame = clearTimeout), window.requestAnimationFrame = requestAnimationFrame, 
    window.cancelAnimationFrame = cancelAnimationFrame;
}(window), Materialize.objectSelectorString = function(obj) {
    return ((obj.prop("tagName") || "") + (obj.attr("id") || "") + (obj.attr("class") || "")).replace(/\s/g, "");
}, Materialize.guid = function() {
    function s4() {
        return Math.floor(65536 * (1 + Math.random())).toString(16).substring(1);
    }
    return function() {
        return s4() + s4() + "-" + s4() + "-" + s4() + "-" + s4() + "-" + s4() + s4() + s4();
    };
}(), Materialize.escapeHash = function(hash) {
    return hash.replace(/(:|\.|\[|\]|,|=)/g, "\\$1");
}, Materialize.elementOrParentIsFixed = function(element) {
    var $element = $(element), $checkElements = $element.add($element.parents()), isFixed = !1;
    return $checkElements.each(function() {
        if ("fixed" === $(this).css("position")) return !(isFixed = !0);
    }), isFixed;
};

var Vel, getTime = Date.now || function() {
    return new Date().getTime();
};

Materialize.throttle = function(func, wait, options) {
    var context, args, result, timeout = null, previous = 0;
    options || (options = {});
    var later = function() {
        previous = !1 === options.leading ? 0 : getTime(), timeout = null, result = func.apply(context, args), 
        context = args = null;
    };
    return function() {
        var now = getTime();
        previous || !1 !== options.leading || (previous = now);
        var remaining = wait - (now - previous);
        return context = this, args = arguments, remaining <= 0 ? (clearTimeout(timeout), 
        timeout = null, previous = now, result = func.apply(context, args), context = args = null) : timeout || !1 === options.trailing || (timeout = setTimeout(later, remaining)), 
        result;
    };
}, Vel = jQuery ? jQuery.Velocity : $ ? $.Velocity : Velocity, Materialize.Vel = Vel || Velocity, 
"undefined" == typeof jQuery && ("function" == typeof require ? jQuery = $ = require("jquery") : jQuery = $), 
function(factory) {
    "function" == typeof define && define.amd ? define([ "jquery" ], function($) {
        return factory($);
    }) : "object" == typeof module && "object" == typeof module.exports ? exports = factory(require("jquery")) : factory(jQuery);
}(function($) {
    $.easing.jswing = $.easing.swing;
    var pow = Math.pow, sqrt = Math.sqrt, sin = Math.sin, cos = Math.cos, PI = Math.PI, c1 = 1.70158, c2 = 1.525 * c1, c4 = 2 * PI / 3, c5 = 2 * PI / 4.5;
    function bounceOut(x) {
        var n1 = 7.5625, d1 = 2.75;
        return x < 1 / d1 ? n1 * x * x : x < 2 / d1 ? n1 * (x -= 1.5 / d1) * x + .75 : x < 2.5 / d1 ? n1 * (x -= 2.25 / d1) * x + .9375 : n1 * (x -= 2.625 / d1) * x + .984375;
    }
    $.extend($.easing, {
        def: "easeOutQuad",
        swing: function(x) {
            return $.easing[$.easing.def](x);
        },
        easeInQuad: function(x) {
            return x * x;
        },
        easeOutQuad: function(x) {
            return 1 - (1 - x) * (1 - x);
        },
        easeInOutQuad: function(x) {
            return x < .5 ? 2 * x * x : 1 - pow(-2 * x + 2, 2) / 2;
        },
        easeInCubic: function(x) {
            return x * x * x;
        },
        easeOutCubic: function(x) {
            return 1 - pow(1 - x, 3);
        },
        easeInOutCubic: function(x) {
            return x < .5 ? 4 * x * x * x : 1 - pow(-2 * x + 2, 3) / 2;
        },
        easeInQuart: function(x) {
            return x * x * x * x;
        },
        easeOutQuart: function(x) {
            return 1 - pow(1 - x, 4);
        },
        easeInOutQuart: function(x) {
            return x < .5 ? 8 * x * x * x * x : 1 - pow(-2 * x + 2, 4) / 2;
        },
        easeInQuint: function(x) {
            return x * x * x * x * x;
        },
        easeOutQuint: function(x) {
            return 1 - pow(1 - x, 5);
        },
        easeInOutQuint: function(x) {
            return x < .5 ? 16 * x * x * x * x * x : 1 - pow(-2 * x + 2, 5) / 2;
        },
        easeInSine: function(x) {
            return 1 - cos(x * PI / 2);
        },
        easeOutSine: function(x) {
            return sin(x * PI / 2);
        },
        easeInOutSine: function(x) {
            return -(cos(PI * x) - 1) / 2;
        },
        easeInExpo: function(x) {
            return 0 === x ? 0 : pow(2, 10 * x - 10);
        },
        easeOutExpo: function(x) {
            return 1 === x ? 1 : 1 - pow(2, -10 * x);
        },
        easeInOutExpo: function(x) {
            return 0 === x ? 0 : 1 === x ? 1 : x < .5 ? pow(2, 20 * x - 10) / 2 : (2 - pow(2, -20 * x + 10)) / 2;
        },
        easeInCirc: function(x) {
            return 1 - sqrt(1 - pow(x, 2));
        },
        easeOutCirc: function(x) {
            return sqrt(1 - pow(x - 1, 2));
        },
        easeInOutCirc: function(x) {
            return x < .5 ? (1 - sqrt(1 - pow(2 * x, 2))) / 2 : (sqrt(1 - pow(-2 * x + 2, 2)) + 1) / 2;
        },
        easeInElastic: function(x) {
            return 0 === x ? 0 : 1 === x ? 1 : -pow(2, 10 * x - 10) * sin((10 * x - 10.75) * c4);
        },
        easeOutElastic: function(x) {
            return 0 === x ? 0 : 1 === x ? 1 : pow(2, -10 * x) * sin((10 * x - .75) * c4) + 1;
        },
        easeInOutElastic: function(x) {
            return 0 === x ? 0 : 1 === x ? 1 : x < .5 ? -pow(2, 20 * x - 10) * sin((20 * x - 11.125) * c5) / 2 : pow(2, -20 * x + 10) * sin((20 * x - 11.125) * c5) / 2 + 1;
        },
        easeInBack: function(x) {
            return 2.70158 * x * x * x - c1 * x * x;
        },
        easeOutBack: function(x) {
            return 1 + 2.70158 * pow(x - 1, 3) + c1 * pow(x - 1, 2);
        },
        easeInOutBack: function(x) {
            return x < .5 ? pow(2 * x, 2) * (7.189819 * x - c2) / 2 : (pow(2 * x - 2, 2) * ((c2 + 1) * (2 * x - 2) + c2) + 2) / 2;
        },
        easeInBounce: function(x) {
            return 1 - bounceOut(1 - x);
        },
        easeOutBounce: bounceOut,
        easeInOutBounce: function(x) {
            return x < .5 ? (1 - bounceOut(1 - 2 * x)) / 2 : (1 + bounceOut(2 * x - 1)) / 2;
        }
    });
}), function(factory) {
    "function" == typeof define && define.amd ? define([ "jquery", "hammerjs" ], factory) : "object" == typeof exports ? factory(require("jquery"), require("hammerjs")) : factory(jQuery, Hammer);
}(function($, Hammer) {
    var originalEmit;
    $.fn.hammer = function(options) {
        return this.each(function() {
            !function(el, options) {
                var $el = $(el);
                $el.data("hammer") || $el.data("hammer", new Hammer($el[0], options));
            }(this, options);
        });
    }, Hammer.Manager.prototype.emit = (originalEmit = Hammer.Manager.prototype.emit, 
    function(type, data) {
        originalEmit.call(this, type, data), $(this.element).trigger({
            type: type,
            gesture: data
        });
    });
}), function($) {
    $.fn.materialbox = function() {
        return this.each(function() {
            if (!$(this).hasClass("initialized")) {
                $(this).addClass("initialized");
                var ancestorsChanged, ancestor, overlayActive = !1, doneAnimating = !0, outDuration = 200, origin = $(this), placeholder = $("<div></div>").addClass("material-placeholder"), originInlineStyles = origin.attr("style");
                origin.wrap(placeholder), origin.on("click", function() {
                    var placeholder = origin.parent(".material-placeholder"), windowWidth = window.innerWidth, windowHeight = window.innerHeight, originalWidth = origin.width(), originalHeight = origin.height();
                    if (!1 === doneAnimating) return returnToOriginal(), !1;
                    if (overlayActive && !0 === doneAnimating) return returnToOriginal(), !1;
                    doneAnimating = !1, origin.addClass("active"), overlayActive = !0, placeholder.css({
                        width: placeholder[0].getBoundingClientRect().width,
                        height: placeholder[0].getBoundingClientRect().height,
                        position: "relative",
                        top: 0,
                        left: 0
                    }), ancestorsChanged = void 0, ancestor = placeholder[0].parentNode;
                    for (;null !== ancestor && !$(ancestor).is(document); ) {
                        var curr = $(ancestor);
                        "visible" !== curr.css("overflow") && (curr.css("overflow", "visible"), ancestorsChanged = void 0 === ancestorsChanged ? curr : ancestorsChanged.add(curr)), 
                        ancestor = ancestor.parentNode;
                    }
                    origin.css({
                        position: "absolute",
                        "z-index": 1e3,
                        "will-change": "left, top, width, height"
                    }).data("width", originalWidth).data("height", originalHeight);
                    var overlay = $('<div id="materialbox-overlay"></div>').css({
                        opacity: 0
                    }).click(function() {
                        !0 === doneAnimating && returnToOriginal();
                    });
                    origin.before(overlay);
                    var overlayOffset = overlay[0].getBoundingClientRect();
                    if (overlay.css({
                        width: windowWidth,
                        height: windowHeight,
                        left: -1 * overlayOffset.left,
                        top: -1 * overlayOffset.top
                    }), overlay.velocity({
                        opacity: 1
                    }, {
                        duration: 275,
                        queue: !1,
                        easing: "easeOutQuad"
                    }), "" !== origin.data("caption")) {
                        var $photo_caption = $('<div class="materialbox-caption"></div>');
                        $photo_caption.text(origin.data("caption")), $("body").append($photo_caption), $photo_caption.css({
                            display: "inline"
                        }), $photo_caption.velocity({
                            opacity: 1
                        }, {
                            duration: 275,
                            queue: !1,
                            easing: "easeOutQuad"
                        });
                    }
                    var newWidth = 0, newHeight = 0;
                    newHeight = originalHeight / windowHeight < originalWidth / windowWidth ? (newWidth = .9 * windowWidth) * (originalHeight / originalWidth) : (newWidth = .9 * windowHeight * (originalWidth / originalHeight), 
                    .9 * windowHeight), origin.hasClass("responsive-img") ? origin.velocity({
                        "max-width": newWidth,
                        width: originalWidth
                    }, {
                        duration: 0,
                        queue: !1,
                        complete: function() {
                            origin.css({
                                left: 0,
                                top: 0
                            }).velocity({
                                height: newHeight,
                                width: newWidth,
                                left: $(document).scrollLeft() + windowWidth / 2 - origin.parent(".material-placeholder").offset().left - newWidth / 2,
                                top: $(document).scrollTop() + windowHeight / 2 - origin.parent(".material-placeholder").offset().top - newHeight / 2
                            }, {
                                duration: 275,
                                queue: !1,
                                easing: "easeOutQuad",
                                complete: function() {
                                    doneAnimating = !0;
                                }
                            });
                        }
                    }) : origin.css("left", 0).css("top", 0).velocity({
                        height: newHeight,
                        width: newWidth,
                        left: $(document).scrollLeft() + windowWidth / 2 - origin.parent(".material-placeholder").offset().left - newWidth / 2,
                        top: $(document).scrollTop() + windowHeight / 2 - origin.parent(".material-placeholder").offset().top - newHeight / 2
                    }, {
                        duration: 275,
                        queue: !1,
                        easing: "easeOutQuad",
                        complete: function() {
                            doneAnimating = !0;
                        }
                    }), $(window).on("scroll.materialbox", function() {
                        overlayActive && returnToOriginal();
                    }), $(window).on("resize.materialbox", function() {
                        overlayActive && returnToOriginal();
                    }), $(document).on("keyup.materialbox", function(e) {
                        27 === e.keyCode && !0 === doneAnimating && overlayActive && returnToOriginal();
                    });
                });
            }
            function returnToOriginal() {
                doneAnimating = !1;
                var placeholder = origin.parent(".material-placeholder"), originalWidth = (window.innerWidth, 
                window.innerHeight, origin.data("width")), originalHeight = origin.data("height");
                origin.velocity("stop", !0), $("#materialbox-overlay").velocity("stop", !0), $(".materialbox-caption").velocity("stop", !0), 
                $(window).off("scroll.materialbox"), $(document).off("keyup.materialbox"), $(window).off("resize.materialbox"), 
                $("#materialbox-overlay").velocity({
                    opacity: 0
                }, {
                    duration: outDuration,
                    queue: !1,
                    easing: "easeOutQuad",
                    complete: function() {
                        overlayActive = !1, $(this).remove();
                    }
                }), origin.velocity({
                    width: originalWidth,
                    height: originalHeight,
                    left: 0,
                    top: 0
                }, {
                    duration: outDuration,
                    queue: !1,
                    easing: "easeOutQuad",
                    complete: function() {
                        placeholder.css({
                            height: "",
                            width: "",
                            position: "",
                            top: "",
                            left: ""
                        }), origin.removeAttr("style"), origin.attr("style", originInlineStyles), origin.removeClass("active"), 
                        doneAnimating = !0, ancestorsChanged && ancestorsChanged.css("overflow", "");
                    }
                }), $(".materialbox-caption").velocity({
                    opacity: 0
                }, {
                    duration: outDuration,
                    queue: !1,
                    easing: "easeOutQuad",
                    complete: function() {
                        $(this).remove();
                    }
                });
            }
        });
    }, $(document).ready(function() {
        $(".materialboxed").materialbox();
    });
}(jQuery), function($, Vel) {
    "use strict";
    var _defaults = {
        opacity: .5,
        inDuration: 250,
        outDuration: 250,
        ready: void 0,
        complete: void 0,
        dismissible: !0,
        startingTop: "4%",
        endingTop: "10%"
    }, Modal = function() {
        function Modal($el, options) {
            _classCallCheck(this, Modal), $el[0].M_Modal && $el[0].M_Modal.destroy(), this.$el = $el, 
            this.options = $.extend({}, Modal.defaults, options), this.isOpen = !1, (this.$el[0].M_Modal = this).id = $el.attr("id"), 
            this.openingTrigger = void 0, this.$overlay = $('<div class="modal-overlay"></div>'), 
            Modal._increment++, Modal._count++, this.$overlay[0].style.zIndex = 1e3 + 2 * Modal._increment, 
            this.$el[0].style.zIndex = 1e3 + 2 * Modal._increment + 1, this.setupEventHandlers();
        }
        return _createClass(Modal, [ {
            key: "getInstance",
            value: function() {
                return this;
            }
        }, {
            key: "destroy",
            value: function() {
                this.removeEventHandlers(), this.$el[0].removeAttribute("style"), this.$overlay[0].parentNode && this.$overlay[0].parentNode.removeChild(this.$overlay[0]), 
                this.$el[0].M_Modal = void 0, Modal._count--;
            }
        }, {
            key: "setupEventHandlers",
            value: function() {
                this.handleOverlayClickBound = this.handleOverlayClick.bind(this), this.handleModalCloseClickBound = this.handleModalCloseClick.bind(this), 
                1 === Modal._count && document.body.addEventListener("click", this.handleTriggerClick), 
                this.$overlay[0].addEventListener("click", this.handleOverlayClickBound), this.$el[0].addEventListener("click", this.handleModalCloseClickBound);
            }
        }, {
            key: "removeEventHandlers",
            value: function() {
                0 === Modal._count && document.body.removeEventListener("click", this.handleTriggerClick), 
                this.$overlay[0].removeEventListener("click", this.handleOverlayClickBound), this.$el[0].removeEventListener("click", this.handleModalCloseClickBound);
            }
        }, {
            key: "handleTriggerClick",
            value: function(e) {
                var $trigger = $(e.target).closest(".modal-trigger");
                if (e.target && $trigger.length) {
                    var modalId = $trigger[0].getAttribute("href");
                    modalId = modalId ? modalId.slice(1) : $trigger[0].getAttribute("data-target");
                    var modalInstance = document.getElementById(modalId).M_Modal;
                    modalInstance && modalInstance.open($trigger), e.preventDefault();
                }
            }
        }, {
            key: "handleOverlayClick",
            value: function() {
                this.options.dismissible && this.close();
            }
        }, {
            key: "handleModalCloseClick",
            value: function(e) {
                var $closeTrigger = $(e.target).closest(".modal-close");
                e.target && $closeTrigger.length && this.close();
            }
        }, {
            key: "handleKeydown",
            value: function(e) {
                27 === e.keyCode && this.options.dismissible && this.close();
            }
        }, {
            key: "animateIn",
            value: function() {
                var _this = this;
                $.extend(this.$el[0].style, {
                    display: "block",
                    opacity: 0
                }), $.extend(this.$overlay[0].style, {
                    display: "block",
                    opacity: 0
                }), Vel(this.$overlay[0], {
                    opacity: this.options.opacity
                }, {
                    duration: this.options.inDuration,
                    queue: !1,
                    ease: "easeOutCubic"
                });
                var enterVelocityOptions = {
                    duration: this.options.inDuration,
                    queue: !1,
                    ease: "easeOutCubic",
                    complete: function() {
                        "function" == typeof _this.options.ready && _this.options.ready.call(_this, _this.$el, _this.openingTrigger);
                    }
                };
                this.$el[0].classList.contains("bottom-sheet") ? Vel(this.$el[0], {
                    bottom: 0,
                    opacity: 1
                }, enterVelocityOptions) : (Vel.hook(this.$el[0], "scaleX", .7), this.$el[0].style.top = this.options.startingTop, 
                Vel(this.$el[0], {
                    top: this.options.endingTop,
                    opacity: 1,
                    scaleX: 1
                }, enterVelocityOptions));
            }
        }, {
            key: "animateOut",
            value: function() {
                var _this2 = this;
                Vel(this.$overlay[0], {
                    opacity: 0
                }, {
                    duration: this.options.outDuration,
                    queue: !1,
                    ease: "easeOutQuart"
                });
                var exitVelocityOptions = {
                    duration: this.options.outDuration,
                    queue: !1,
                    ease: "easeOutCubic",
                    complete: function() {
                        _this2.$el[0].style.display = "none", "function" == typeof _this2.options.complete && _this2.options.complete.call(_this2, _this2.$el), 
                        _this2.$overlay[0].parentNode.removeChild(_this2.$overlay[0]);
                    }
                };
                this.$el[0].classList.contains("bottom-sheet") ? Vel(this.$el[0], {
                    bottom: "-100%",
                    opacity: 0
                }, exitVelocityOptions) : Vel(this.$el[0], {
                    top: this.options.startingTop,
                    opacity: 0,
                    scaleX: .7
                }, exitVelocityOptions);
            }
        }, {
            key: "open",
            value: function($trigger) {
                if (!this.isOpen) {
                    this.isOpen = !0;
                    var body = document.body;
                    return body.style.overflow = "hidden", this.$el[0].classList.add("open"), body.appendChild(this.$overlay[0]), 
                    this.openingTrigger = $trigger || void 0, this.options.dismissible && (this.handleKeydownBound = this.handleKeydown.bind(this), 
                    document.addEventListener("keydown", this.handleKeydownBound)), this.animateIn(), 
                    this;
                }
            }
        }, {
            key: "close",
            value: function() {
                if (this.isOpen) return this.isOpen = !1, this.$el[0].classList.remove("open"), 
                document.body.style.overflow = "", this.options.dismissible && document.removeEventListener("keydown", this.handleKeydownBound), 
                this.animateOut(), this;
            }
        } ], [ {
            key: "init",
            value: function($els, options) {
                var arr = [];
                return $els.each(function() {
                    arr.push(new Modal($(this), options));
                }), arr;
            }
        }, {
            key: "defaults",
            get: function() {
                return _defaults;
            }
        } ]), Modal;
    }();
    Modal._increment = 0, Modal._count = 0, Materialize.Modal = Modal, $.fn.modal = function(methodOrOptions) {
        return Modal.prototype[methodOrOptions] ? "get" === methodOrOptions.slice(0, 3) ? this.first()[0].M_Modal[methodOrOptions]() : this.each(function() {
            this.M_Modal[methodOrOptions]();
        }) : "object" != typeof methodOrOptions && methodOrOptions ? void $.error("Method " + methodOrOptions + " does not exist on jQuery.modal") : (Modal.init(this, methodOrOptions), 
        this);
    };
}(jQuery, Materialize.Vel), function($) {
    $.fn.parallax = function() {
        var window_width = $(window).width();
        return this.each(function(i) {
            var $this = $(this);
            function updateParallax(initial) {
                var container_height;
                container_height = window_width < 601 ? 0 < $this.height() ? $this.height() : $this.children("img").height() : 0 < $this.height() ? $this.height() : 500;
                var $img = $this.children("img").first(), parallax_dist = $img.height() - container_height, bottom = $this.offset().top + container_height, top = $this.offset().top, scrollTop = $(window).scrollTop(), windowHeight = window.innerHeight, percentScrolled = (scrollTop + windowHeight - top) / (container_height + windowHeight), parallax = Math.round(parallax_dist * percentScrolled);
                initial && $img.css("display", "block"), scrollTop < bottom && top < scrollTop + windowHeight && $img.css("transform", "translate3D(-50%," + parallax + "px, 0)");
            }
            $this.addClass("parallax"), $this.children("img").one("load", function() {
                updateParallax(!0);
            }).each(function() {
                this.complete && $(this).trigger("load");
            }), $(window).scroll(function() {
                window_width = $(window).width(), updateParallax(!1);
            }), $(window).resize(function() {
                window_width = $(window).width(), updateParallax(!1);
            });
        });
    };
}(jQuery), function($) {
    $.fn.pushpin = function(options) {
        var defaults = {
            top: 0,
            bottom: 1 / 0,
            offset: 0
        };
        return "remove" === options ? (this.each(function() {
            (id = $(this).data("pushpin-id")) && ($(window).off("scroll." + id), $(this).removeData("pushpin-id").removeClass("pin-top pinned pin-bottom").removeAttr("style"));
        }), !1) : (options = $.extend(defaults, options), $index = 0, this.each(function() {
            var $uniqueId = Materialize.guid(), $this = $(this), $original_offset = $(this).offset().top;
            function removePinClasses(object) {
                object.removeClass("pin-top"), object.removeClass("pinned"), object.removeClass("pin-bottom");
            }
            function updateElements(objects, scrolled) {
                objects.each(function() {
                    options.top <= scrolled && options.bottom >= scrolled && !$(this).hasClass("pinned") && (removePinClasses($(this)), 
                    $(this).css("top", options.offset), $(this).addClass("pinned")), scrolled < options.top && !$(this).hasClass("pin-top") && (removePinClasses($(this)), 
                    $(this).css("top", 0), $(this).addClass("pin-top")), scrolled > options.bottom && !$(this).hasClass("pin-bottom") && (removePinClasses($(this)), 
                    $(this).addClass("pin-bottom"), $(this).css("top", options.bottom - $original_offset));
                });
            }
            $(this).data("pushpin-id", $uniqueId), updateElements($this, $(window).scrollTop()), 
            $(window).on("scroll." + $uniqueId, function() {
                var $scrolled = $(window).scrollTop() + options.offset;
                updateElements($this, $scrolled);
            });
        }));
    };
}(jQuery), function($) {
    var scrollFireEventsHandled = !1;
    Materialize.scrollFire = function(options) {
        var throttledScroll = Materialize.throttle(function() {
            !function() {
                for (var windowScroll = window.pageYOffset + window.innerHeight, i = 0; i < options.length; i++) {
                    var value = options[i], selector = value.selector, offset = value.offset, callback = value.callback, currentElement = document.querySelector(selector);
                    null !== currentElement && currentElement.getBoundingClientRect().top + window.pageYOffset + offset < windowScroll && !0 !== value.done && ("function" == typeof callback ? callback.call(this, currentElement) : "string" == typeof callback && new Function(callback)(currentElement), 
                    value.done = !0);
                }
            }();
        }, options.throttle || 100);
        scrollFireEventsHandled || (window.addEventListener("scroll", throttledScroll), 
        window.addEventListener("resize", throttledScroll), scrollFireEventsHandled = !0), 
        setTimeout(throttledScroll, 0);
    };
}(jQuery), function($) {
    var jWindow = $(window), elements = [], elementsInView = [], isSpying = !1, ticks = 0, offset = {
        top: 0,
        right: 0,
        bottom: 0,
        left: 0
    };
    function onScroll(scrollOffset) {
        ++ticks;
        var top = jWindow.scrollTop(), left = jWindow.scrollLeft(), right = left + jWindow.width(), bottom = top + jWindow.height(), intersections = function(top, right, bottom, left) {
            var hits = $();
            return $.each(elements, function(i, element) {
                if (0 < element.height()) {
                    var elTop = element.offset().top, elLeft = element.offset().left, elRight = elLeft + element.width(), elBottom = elTop + element.height();
                    !(right < elLeft || elRight < left || bottom < elTop || elBottom < top) && hits.push(element);
                }
            }), hits;
        }(top + offset.top + scrollOffset || 200, right + offset.right, bottom + offset.bottom, left + offset.left);
        $.each(intersections, function(i, element) {
            "number" != typeof element.data("scrollSpy:ticks") && element.triggerHandler("scrollSpy:enter"), 
            element.data("scrollSpy:ticks", ticks);
        }), $.each(elementsInView, function(i, element) {
            var lastTick = element.data("scrollSpy:ticks");
            "number" == typeof lastTick && lastTick !== ticks && (element.triggerHandler("scrollSpy:exit"), 
            element.data("scrollSpy:ticks", null));
        }), elementsInView = intersections;
    }
    function onWinSize() {
        jWindow.trigger("scrollSpy:winSize");
    }
    $.scrollSpy = function(selector, options) {
        options = $.extend({
            throttle: 100,
            scrollOffset: 200,
            activeClass: "active",
            getActiveElement: function(id) {
                return 'a[href="#' + id + '"]';
            }
        }, options);
        var visible = [];
        (selector = $(selector)).each(function(i, element) {
            elements.push($(element)), $(element).data("scrollSpy:id", i), $('a[href="#' + $(element).attr("id") + '"]').click(function(e) {
                e.preventDefault();
                var offset = $(Materialize.escapeHash(this.hash)).offset().top + 1;
                $("html, body").animate({
                    scrollTop: offset - options.scrollOffset
                }, {
                    duration: 400,
                    queue: !1,
                    easing: "easeOutCubic"
                });
            });
        }), offset.top = options.offsetTop || 0, offset.right = options.offsetRight || 0, 
        offset.bottom = options.offsetBottom || 0, offset.left = options.offsetLeft || 0;
        var throttledScroll = Materialize.throttle(function() {
            onScroll(options.scrollOffset);
        }, options.throttle || 100), readyScroll = function() {
            $(document).ready(throttledScroll);
        };
        return isSpying || (jWindow.on("scroll", readyScroll), jWindow.on("resize", readyScroll), 
        isSpying = !0), setTimeout(readyScroll, 0), selector.on("scrollSpy:enter", function() {
            visible = $.grep(visible, function(value) {
                return 0 != value.height();
            });
            var $this = $(this);
            visible[0] ? ($(options.getActiveElement(visible[0].attr("id"))).removeClass(options.activeClass), 
            $this.data("scrollSpy:id") < visible[0].data("scrollSpy:id") ? visible.unshift($(this)) : visible.push($(this))) : visible.push($(this)), 
            $(options.getActiveElement(visible[0].attr("id"))).addClass(options.activeClass);
        }), selector.on("scrollSpy:exit", function() {
            if ((visible = $.grep(visible, function(value) {
                return 0 != value.height();
            }))[0]) {
                $(options.getActiveElement(visible[0].attr("id"))).removeClass(options.activeClass);
                var $this = $(this);
                (visible = $.grep(visible, function(value) {
                    return value.attr("id") != $this.attr("id");
                }))[0] && $(options.getActiveElement(visible[0].attr("id"))).addClass(options.activeClass);
            }
        }), selector;
    }, $.winSizeSpy = function(options) {
        return $.winSizeSpy = function() {
            return jWindow;
        }, options = options || {
            throttle: 100
        }, jWindow.on("resize", Materialize.throttle(onWinSize, options.throttle || 100));
    }, $.fn.scrollSpy = function(options) {
        return $.scrollSpy($(this), options);
    };
}(jQuery), function($) {
    var methods = {
        init: function(options) {
            options = $.extend({
                menuWidth: 300,
                edge: "left",
                closeOnClick: !1,
                draggable: !0,
                onOpen: null,
                onClose: null
            }, options), $(this).each(function() {
                var $this = $(this), menuId = $this.attr("data-activates"), menu = $("#" + menuId);
                300 != options.menuWidth && menu.css("width", options.menuWidth);
                var $dragTarget = $('.drag-target[data-sidenav="' + menuId + '"]');
                options.draggable ? ($dragTarget.length && $dragTarget.remove(), $dragTarget = $('<div class="drag-target"></div>').attr("data-sidenav", menuId), 
                $("body").append($dragTarget)) : $dragTarget = $(), "left" == options.edge ? (menu.css("transform", "translateX(-100%)"), 
                $dragTarget.css({
                    left: 0
                })) : (menu.addClass("right-aligned").css("transform", "translateX(100%)"), $dragTarget.css({
                    right: 0
                })), menu.hasClass("fixed") && 992 < window.innerWidth && menu.css("transform", "translateX(0)"), 
                menu.hasClass("fixed") && $(window).resize(function() {
                    992 < window.innerWidth ? 0 !== $("#sidenav-overlay").length && menuOut ? removeMenu(!0) : menu.css("transform", "translateX(0%)") : !1 === menuOut && ("left" === options.edge ? menu.css("transform", "translateX(-100%)") : menu.css("transform", "translateX(100%)"));
                }), !0 === options.closeOnClick && menu.on("click.itemclick", "a:not(.collapsible-header)", function() {
                    992 < window.innerWidth && menu.hasClass("fixed") || removeMenu();
                });
                var removeMenu = function(restoreNav) {
                    menuOut = !1, $("body").css({
                        overflow: "",
                        width: ""
                    }), $("#sidenav-overlay").velocity({
                        opacity: 0
                    }, {
                        duration: 200,
                        queue: !1,
                        easing: "easeOutQuad",
                        complete: function() {
                            $(this).remove();
                        }
                    }), "left" === options.edge ? ($dragTarget.css({
                        width: "",
                        right: "",
                        left: "0"
                    }), menu.velocity({
                        translateX: "-100%"
                    }, {
                        duration: 200,
                        queue: !1,
                        easing: "easeOutCubic",
                        complete: function() {
                            !0 === restoreNav && (menu.removeAttr("style"), menu.css("width", options.menuWidth));
                        }
                    })) : ($dragTarget.css({
                        width: "",
                        right: "0",
                        left: ""
                    }), menu.velocity({
                        translateX: "100%"
                    }, {
                        duration: 200,
                        queue: !1,
                        easing: "easeOutCubic",
                        complete: function() {
                            !0 === restoreNav && (menu.removeAttr("style"), menu.css("width", options.menuWidth));
                        }
                    })), "function" == typeof options.onClose && options.onClose.call(this, menu);
                }, menuOut = !1;
                options.draggable && ($dragTarget.on("click", function() {
                    menuOut && removeMenu();
                }), $dragTarget.hammer({
                    prevent_default: !1
                }).on("pan", function(e) {
                    if ("touch" == e.gesture.pointerType) {
                        e.gesture.direction;
                        var x = e.gesture.center.x, y = e.gesture.center.y;
                        e.gesture.velocityX;
                        if (0 === x && 0 === y) return;
                        var overlayPerc, $body = $("body"), $overlay = $("#sidenav-overlay"), oldWidth = $body.innerWidth();
                        if ($body.css("overflow", "hidden"), $body.width(oldWidth), 0 === $overlay.length && (($overlay = $('<div id="sidenav-overlay"></div>')).css("opacity", 0).click(function() {
                            removeMenu();
                        }), "function" == typeof options.onOpen && options.onOpen.call(this, menu), $("body").append($overlay)), 
                        "left" === options.edge && (x > options.menuWidth ? x = options.menuWidth : x < 0 && (x = 0)), 
                        "left" === options.edge) x < options.menuWidth / 2 ? menuOut = !1 : x >= options.menuWidth / 2 && (menuOut = !0), 
                        menu.css("transform", "translateX(" + (x - options.menuWidth) + "px)"); else {
                            x < window.innerWidth - options.menuWidth / 2 ? menuOut = !0 : x >= window.innerWidth - options.menuWidth / 2 && (menuOut = !1);
                            var rightPos = x - options.menuWidth / 2;
                            rightPos < 0 && (rightPos = 0), menu.css("transform", "translateX(" + rightPos + "px)");
                        }
                        overlayPerc = "left" === options.edge ? x / options.menuWidth : Math.abs((x - window.innerWidth) / options.menuWidth), 
                        $overlay.velocity({
                            opacity: overlayPerc
                        }, {
                            duration: 10,
                            queue: !1,
                            easing: "easeOutQuad"
                        });
                    }
                }).on("panend", function(e) {
                    if ("touch" == e.gesture.pointerType) {
                        var $overlay = $("#sidenav-overlay"), velocityX = e.gesture.velocityX, x = e.gesture.center.x, leftPos = x - options.menuWidth, rightPos = x - options.menuWidth / 2;
                        0 < leftPos && (leftPos = 0), rightPos < 0 && (rightPos = 0), !1, "left" === options.edge ? menuOut && velocityX <= .3 || velocityX < -.5 ? (0 !== leftPos && menu.velocity({
                            translateX: [ 0, leftPos ]
                        }, {
                            duration: 300,
                            queue: !1,
                            easing: "easeOutQuad"
                        }), $overlay.velocity({
                            opacity: 1
                        }, {
                            duration: 50,
                            queue: !1,
                            easing: "easeOutQuad"
                        }), $dragTarget.css({
                            width: "50%",
                            right: 0,
                            left: ""
                        }), menuOut = !0) : (!menuOut || .3 < velocityX) && ($("body").css({
                            overflow: "",
                            width: ""
                        }), menu.velocity({
                            translateX: [ -1 * options.menuWidth - 10, leftPos ]
                        }, {
                            duration: 200,
                            queue: !1,
                            easing: "easeOutQuad"
                        }), $overlay.velocity({
                            opacity: 0
                        }, {
                            duration: 200,
                            queue: !1,
                            easing: "easeOutQuad",
                            complete: function() {
                                "function" == typeof options.onClose && options.onClose.call(this, menu), $(this).remove();
                            }
                        }), $dragTarget.css({
                            width: "10px",
                            right: "",
                            left: 0
                        })) : menuOut && -.3 <= velocityX || .5 < velocityX ? (0 !== rightPos && menu.velocity({
                            translateX: [ 0, rightPos ]
                        }, {
                            duration: 300,
                            queue: !1,
                            easing: "easeOutQuad"
                        }), $overlay.velocity({
                            opacity: 1
                        }, {
                            duration: 50,
                            queue: !1,
                            easing: "easeOutQuad"
                        }), $dragTarget.css({
                            width: "50%",
                            right: "",
                            left: 0
                        }), menuOut = !0) : (!menuOut || velocityX < -.3) && ($("body").css({
                            overflow: "",
                            width: ""
                        }), menu.velocity({
                            translateX: [ options.menuWidth + 10, rightPos ]
                        }, {
                            duration: 200,
                            queue: !1,
                            easing: "easeOutQuad"
                        }), $overlay.velocity({
                            opacity: 0
                        }, {
                            duration: 200,
                            queue: !1,
                            easing: "easeOutQuad",
                            complete: function() {
                                "function" == typeof options.onClose && options.onClose.call(this, menu), $(this).remove();
                            }
                        }), $dragTarget.css({
                            width: "10px",
                            right: 0,
                            left: ""
                        }));
                    }
                })), $this.off("click.sidenav").on("click.sidenav", function() {
                    if (!0 === menuOut) menuOut = !1, removeMenu(); else {
                        var $body = $("body"), $overlay = $('<div id="sidenav-overlay"></div>'), oldWidth = $body.innerWidth();
                        $body.css("overflow", "hidden"), $body.width(oldWidth), $("body").append($dragTarget), 
                        "left" === options.edge ? ($dragTarget.css({
                            width: "50%",
                            right: 0,
                            left: ""
                        }), menu.velocity({
                            translateX: [ 0, -1 * options.menuWidth ]
                        }, {
                            duration: 300,
                            queue: !1,
                            easing: "easeOutQuad"
                        })) : ($dragTarget.css({
                            width: "50%",
                            right: "",
                            left: 0
                        }), menu.velocity({
                            translateX: [ 0, options.menuWidth ]
                        }, {
                            duration: 300,
                            queue: !1,
                            easing: "easeOutQuad"
                        })), $overlay.css("opacity", 0).click(function() {
                            menuOut = !1, removeMenu(), $overlay.velocity({
                                opacity: 0
                            }, {
                                duration: 300,
                                queue: !1,
                                easing: "easeOutQuad",
                                complete: function() {
                                    $(this).remove();
                                }
                            });
                        }), $("body").append($overlay), $overlay.velocity({
                            opacity: 1
                        }, {
                            duration: 300,
                            queue: !1,
                            easing: "easeOutQuad",
                            complete: function() {
                                !(menuOut = !0);
                            }
                        }), "function" == typeof options.onOpen && options.onOpen.call(this, menu);
                    }
                    return !1;
                });
            });
        },
        destroy: function() {
            var $overlay = $("#sidenav-overlay"), $dragTarget = $('.drag-target[data-sidenav="' + $(this).attr("data-activates") + '"]');
            $overlay.trigger("click"), $dragTarget.remove(), $(this).off("click"), $overlay.remove();
        },
        show: function() {
            this.trigger("click");
        },
        hide: function() {
            $("#sidenav-overlay").trigger("click");
        }
    };
    $.fn.sideNav = function(methodOrOptions) {
        return methods[methodOrOptions] ? methods[methodOrOptions].apply(this, Array.prototype.slice.call(arguments, 1)) : "object" != typeof methodOrOptions && methodOrOptions ? void $.error("Method " + methodOrOptions + " does not exist on jQuery.sideNav") : methods.init.apply(this, arguments);
    };
}(jQuery), function($) {
    var methods = {
        init: function(options) {
            return options = $.extend({
                indicators: !0,
                height: 400,
                transition: 500,
                interval: 6e3
            }, options), this.each(function() {
                var $active, $indicators, $interval, $this = $(this), $slider = $this.find("ul.slides").first(), $slides = $slider.find("> li"), $active_index = $slider.find(".active").index();
                function captionTransition(caption, duration) {
                    caption.hasClass("center-align") ? caption.velocity({
                        opacity: 0,
                        translateY: -100
                    }, {
                        duration: duration,
                        queue: !1
                    }) : caption.hasClass("right-align") ? caption.velocity({
                        opacity: 0,
                        translateX: 100
                    }, {
                        duration: duration,
                        queue: !1
                    }) : caption.hasClass("left-align") && caption.velocity({
                        opacity: 0,
                        translateX: -100
                    }, {
                        duration: duration,
                        queue: !1
                    });
                }
                function moveToSlide(index) {
                    index >= $slides.length ? index = 0 : index < 0 && (index = $slides.length - 1), 
                    ($active_index = $slider.find(".active").index()) != index && ($active = $slides.eq($active_index), 
                    $caption = $active.find(".caption"), $active.removeClass("active"), $active.velocity({
                        opacity: 0
                    }, {
                        duration: options.transition,
                        queue: !1,
                        easing: "easeOutQuad",
                        complete: function() {
                            $slides.not(".active").velocity({
                                opacity: 0,
                                translateX: 0,
                                translateY: 0
                            }, {
                                duration: 0,
                                queue: !1
                            });
                        }
                    }), captionTransition($caption, options.transition), options.indicators && $indicators.eq($active_index).removeClass("active"), 
                    $slides.eq(index).velocity({
                        opacity: 1
                    }, {
                        duration: options.transition,
                        queue: !1,
                        easing: "easeOutQuad"
                    }), $slides.eq(index).find(".caption").velocity({
                        opacity: 1,
                        translateX: 0,
                        translateY: 0
                    }, {
                        duration: options.transition,
                        delay: options.transition,
                        queue: !1,
                        easing: "easeOutQuad"
                    }), $slides.eq(index).addClass("active"), options.indicators && $indicators.eq(index).addClass("active"));
                }
                -1 != $active_index && ($active = $slides.eq($active_index)), $this.hasClass("fullscreen") || (options.indicators ? $this.height(options.height + 40) : $this.height(options.height), 
                $slider.height(options.height)), $slides.find(".caption").each(function() {
                    captionTransition($(this), 0);
                }), $slides.find("img").each(function() {
                    var placeholderBase64 = "data:image/gif;base64,R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";
                    $(this).attr("src") !== placeholderBase64 && ($(this).css("background-image", 'url("' + $(this).attr("src") + '")'), 
                    $(this).attr("src", placeholderBase64));
                }), options.indicators && ($indicators = $('<ul class="indicators"></ul>'), $slides.each(function(index) {
                    var $indicator = $('<li class="indicator-item"></li>');
                    $indicator.click(function() {
                        moveToSlide($slider.parent().find($(this)).index()), clearInterval($interval), $interval = setInterval(function() {
                            $active_index = $slider.find(".active").index(), $slides.length == $active_index + 1 ? $active_index = 0 : $active_index += 1, 
                            moveToSlide($active_index);
                        }, options.transition + options.interval);
                    }), $indicators.append($indicator);
                }), $this.append($indicators), $indicators = $this.find("ul.indicators").find("li.indicator-item")), 
                $active ? $active.show() : ($slides.first().addClass("active").velocity({
                    opacity: 1
                }, {
                    duration: options.transition,
                    queue: !1,
                    easing: "easeOutQuad"
                }), $active_index = 0, $active = $slides.eq($active_index), options.indicators && $indicators.eq($active_index).addClass("active")), 
                $active.find("img").each(function() {
                    $active.find(".caption").velocity({
                        opacity: 1,
                        translateX: 0,
                        translateY: 0
                    }, {
                        duration: options.transition,
                        queue: !1,
                        easing: "easeOutQuad"
                    });
                }), $interval = setInterval(function() {
                    moveToSlide(($active_index = $slider.find(".active").index()) + 1);
                }, options.transition + options.interval);
                var swipeLeft = !1, swipeRight = !1;
                $this.hammer({
                    prevent_default: !1
                }).on("pan", function(e) {
                    if ("touch" === e.gesture.pointerType) {
                        clearInterval($interval);
                        var next_slide, direction = e.gesture.direction, x = e.gesture.deltaX, velocityX = e.gesture.velocityX, velocityY = e.gesture.velocityY;
                        $curr_slide = $slider.find(".active"), Math.abs(velocityX) > Math.abs(velocityY) && $curr_slide.velocity({
                            translateX: x
                        }, {
                            duration: 50,
                            queue: !1,
                            easing: "easeOutQuad"
                        }), 4 === direction && (x > $this.innerWidth() / 2 || velocityX < -.65) ? swipeRight = !0 : 2 === direction && (x < -1 * $this.innerWidth() / 2 || .65 < velocityX) && (swipeLeft = !0), 
                        swipeLeft && (0 === (next_slide = $curr_slide.next()).length && (next_slide = $slides.first()), 
                        next_slide.velocity({
                            opacity: 1
                        }, {
                            duration: 300,
                            queue: !1,
                            easing: "easeOutQuad"
                        })), swipeRight && (0 === (next_slide = $curr_slide.prev()).length && (next_slide = $slides.last()), 
                        next_slide.velocity({
                            opacity: 1
                        }, {
                            duration: 300,
                            queue: !1,
                            easing: "easeOutQuad"
                        }));
                    }
                }).on("panend", function(e) {
                    "touch" === e.gesture.pointerType && ($curr_slide = $slider.find(".active"), !1, 
                    curr_index = $slider.find(".active").index(), !swipeRight && !swipeLeft || $slides.length <= 1 ? $curr_slide.velocity({
                        translateX: 0
                    }, {
                        duration: 300,
                        queue: !1,
                        easing: "easeOutQuad"
                    }) : swipeLeft ? (moveToSlide(curr_index + 1), $curr_slide.velocity({
                        translateX: -1 * $this.innerWidth()
                    }, {
                        duration: 300,
                        queue: !1,
                        easing: "easeOutQuad",
                        complete: function() {
                            $curr_slide.velocity({
                                opacity: 0,
                                translateX: 0
                            }, {
                                duration: 0,
                                queue: !1
                            });
                        }
                    })) : swipeRight && (moveToSlide(curr_index - 1), $curr_slide.velocity({
                        translateX: $this.innerWidth()
                    }, {
                        duration: 300,
                        queue: !1,
                        easing: "easeOutQuad",
                        complete: function() {
                            $curr_slide.velocity({
                                opacity: 0,
                                translateX: 0
                            }, {
                                duration: 0,
                                queue: !1
                            });
                        }
                    })), swipeRight = swipeLeft = !1, clearInterval($interval), $interval = setInterval(function() {
                        $active_index = $slider.find(".active").index(), $slides.length == $active_index + 1 ? $active_index = 0 : $active_index += 1, 
                        moveToSlide($active_index);
                    }, options.transition + options.interval));
                }), $this.on("sliderPause", function() {
                    clearInterval($interval);
                }), $this.on("sliderStart", function() {
                    clearInterval($interval), $interval = setInterval(function() {
                        $active_index = $slider.find(".active").index(), $slides.length == $active_index + 1 ? $active_index = 0 : $active_index += 1, 
                        moveToSlide($active_index);
                    }, options.transition + options.interval);
                }), $this.on("sliderNext", function() {
                    moveToSlide(($active_index = $slider.find(".active").index()) + 1);
                }), $this.on("sliderPrev", function() {
                    moveToSlide(($active_index = $slider.find(".active").index()) - 1);
                });
            });
        },
        pause: function() {
            $(this).trigger("sliderPause");
        },
        start: function() {
            $(this).trigger("sliderStart");
        },
        next: function() {
            $(this).trigger("sliderNext");
        },
        prev: function() {
            $(this).trigger("sliderPrev");
        }
    };
    $.fn.slider = function(methodOrOptions) {
        return methods[methodOrOptions] ? methods[methodOrOptions].apply(this, Array.prototype.slice.call(arguments, 1)) : "object" != typeof methodOrOptions && methodOrOptions ? void $.error("Method " + methodOrOptions + " does not exist on jQuery.tooltip") : methods.init.apply(this, arguments);
    };
}(jQuery), function($) {
    var methods = {
        init: function(options) {
            var defaults = {
                onShow: null,
                swipeable: !1,
                responsiveThreshold: 1 / 0
            };
            options = $.extend(defaults, options);
            var namespace = Materialize.objectSelectorString($(this));
            return this.each(function(i) {
                var $active, $content, $tabs_wrapper, $indicator, uniqueNamespace = namespace + i, $this = $(this), window_width = $(window).width(), $links = $this.find("li.tab a"), $tabs_width = $this.width(), $tabs_content = $(), $tab_width = Math.max($tabs_width, $this[0].scrollWidth) / $links.length, index = 0, prev_index = 0, clicked = !1, calcRightPos = function(el) {
                    return Math.ceil($tabs_width - el.position().left - el[0].getBoundingClientRect().width - $this.scrollLeft());
                }, calcLeftPos = function(el) {
                    return Math.floor(el.position().left + $this.scrollLeft());
                }, animateIndicator = function(prev_index) {
                    0 <= index - prev_index ? ($indicator.velocity({
                        right: calcRightPos($active)
                    }, {
                        duration: 300,
                        queue: !1,
                        easing: "easeOutQuad"
                    }), $indicator.velocity({
                        left: calcLeftPos($active)
                    }, {
                        duration: 300,
                        queue: !1,
                        easing: "easeOutQuad",
                        delay: 90
                    })) : ($indicator.velocity({
                        left: calcLeftPos($active)
                    }, {
                        duration: 300,
                        queue: !1,
                        easing: "easeOutQuad"
                    }), $indicator.velocity({
                        right: calcRightPos($active)
                    }, {
                        duration: 300,
                        queue: !1,
                        easing: "easeOutQuad",
                        delay: 90
                    }));
                };
                options.swipeable && window_width > options.responsiveThreshold && (options.swipeable = !1), 
                0 === ($active = $($links.filter('[href="' + location.hash + '"]'))).length && ($active = $(this).find("li.tab a.active").first()), 
                0 === $active.length && ($active = $(this).find("li.tab a").first()), $active.addClass("active"), 
                (index = $links.index($active)) < 0 && (index = 0), void 0 !== $active[0] && ($content = $($active[0].hash)).addClass("active"), 
                $this.find(".indicator").length || $this.append('<li class="indicator"></li>'), 
                $indicator = $this.find(".indicator"), $this.append($indicator), $this.is(":visible") && setTimeout(function() {
                    $indicator.css({
                        right: calcRightPos($active)
                    }), $indicator.css({
                        left: calcLeftPos($active)
                    });
                }, 0), $(window).off("resize.tabs-" + uniqueNamespace).on("resize.tabs-" + uniqueNamespace, function() {
                    $tabs_width = $this.width(), $tab_width = Math.max($tabs_width, $this[0].scrollWidth) / $links.length, 
                    index < 0 && (index = 0), 0 !== $tab_width && 0 !== $tabs_width && ($indicator.css({
                        right: calcRightPos($active)
                    }), $indicator.css({
                        left: calcLeftPos($active)
                    }));
                }), options.swipeable ? ($links.each(function() {
                    var $curr_content = $(Materialize.escapeHash(this.hash));
                    $curr_content.addClass("carousel-item"), $tabs_content = $tabs_content.add($curr_content);
                }), $tabs_wrapper = $tabs_content.wrapAll('<div class="tabs-content carousel"></div>'), 
                $tabs_content.css("display", ""), $(".tabs-content.carousel").carousel({
                    fullWidth: !0,
                    noWrap: !0,
                    onCycleTo: function(item) {
                        if (!clicked) {
                            var prev_index = index;
                            index = $tabs_wrapper.index(item), $active.removeClass("active"), ($active = $links.eq(index)).addClass("active"), 
                            animateIndicator(prev_index), "function" == typeof options.onShow && options.onShow.call($this[0], $content);
                        }
                    }
                })) : $links.not($active).each(function() {
                    $(Materialize.escapeHash(this.hash)).hide();
                }), $this.off("click.tabs").on("click.tabs", "a", function(e) {
                    if ($(this).parent().hasClass("disabled")) e.preventDefault(); else if (!$(this).attr("target")) {
                        clicked = !0, $tabs_width = $this.width(), $tab_width = Math.max($tabs_width, $this[0].scrollWidth) / $links.length, 
                        $active.removeClass("active");
                        var $oldContent = $content;
                        $active = $(this), $content = $(Materialize.escapeHash(this.hash)), $links = $this.find("li.tab a");
                        $active.position();
                        $active.addClass("active"), prev_index = index, (index = $links.index($(this))) < 0 && (index = 0), 
                        options.swipeable ? $tabs_content.length && $tabs_content.carousel("set", index, function() {
                            "function" == typeof options.onShow && options.onShow.call($this[0], $content);
                        }) : (void 0 !== $content && ($content.show(), $content.addClass("active"), "function" == typeof options.onShow && options.onShow.call(this, $content)), 
                        void 0 === $oldContent || $oldContent.is($content) || ($oldContent.hide(), $oldContent.removeClass("active"))), 
                        setTimeout(function() {
                            clicked = !1;
                        }, 300), animateIndicator(prev_index), e.preventDefault();
                    }
                });
            });
        },
        select_tab: function(id) {
            this.find('a[href="#' + id + '"]').trigger("click");
        }
    };
    $.fn.tabs = function(methodOrOptions) {
        return methods[methodOrOptions] ? methods[methodOrOptions].apply(this, Array.prototype.slice.call(arguments, 1)) : "object" != typeof methodOrOptions && methodOrOptions ? void $.error("Method " + methodOrOptions + " does not exist on jQuery.tabs") : methods.init.apply(this, arguments);
    }, $(document).ready(function() {
        $("ul.tabs").tabs();
    });
}(jQuery), function($) {
    $.fn.tabsmenu = function(options) {
        this.each(function() {
            var origin = $(this), tabs = $(this).find(".tabs"), rightArrow = $(this).find(".right-arrow"), leftArrow = $(this).find(".left-arrow"), width = 0;
            function computeWith() {
                width = 0, origin.find(".tabs li.tab").each(function() {
                    width += $(this).width();
                }), width = Math.floor(width), origin.width() < width ? rightArrow.show() : rightArrow.hide();
            }
            computeWith(), $(window).resize(function() {
                computeWith();
            }), tabs.bind("scroll", function() {
                $(this).scrollLeft() >= width - $(this).width() ? rightArrow.hide() : rightArrow.show(), 
                $(this).scrollLeft() ? leftArrow.show() : leftArrow.hide();
            });
        });
    }, $(document).ready(function() {
        $(".tabs-container").tabsmenu();
    });
}(jQuery), function($) {
    var methods = {
        init: function(options) {
            return this.each(function() {
                var origin = $("#" + $(this).attr("data-activates")), tapTargetEl = ($("body"), 
                $(this)), tapTargetWrapper = tapTargetEl.parent(".tap-target-wrapper"), tapTargetWave = tapTargetWrapper.find(".tap-target-wave"), tapTargetOriginEl = tapTargetWrapper.find(".tap-target-origin"), tapTargetContentEl = tapTargetEl.find(".tap-target-content");
                tapTargetWrapper.length || (tapTargetWrapper = tapTargetEl.wrap($('<div class="tap-target-wrapper"></div>')).parent()), 
                tapTargetContentEl.length || (tapTargetContentEl = $('<div class="tap-target-content"></div>'), 
                tapTargetEl.append(tapTargetContentEl)), tapTargetWave.length || (tapTargetWave = $('<div class="tap-target-wave"></div>'), 
                tapTargetOriginEl.length || ((tapTargetOriginEl = origin.clone(!0, !0)).addClass("tap-target-origin"), 
                tapTargetOriginEl.removeAttr("id"), tapTargetOriginEl.removeAttr("style"), tapTargetWave.append(tapTargetOriginEl)), 
                tapTargetWrapper.append(tapTargetWave));
                var closeTapTarget = function() {
                    tapTargetWrapper.is(".open") && (tapTargetWrapper.removeClass("open"), tapTargetOriginEl.off("click.tapTarget"), 
                    $(document).off("click.tapTarget"), $(window).off("resize.tapTarget"));
                }, calculateTapTarget = function() {
                    var isFixed = "fixed" === origin.css("position");
                    if (!isFixed) for (var parents = origin.parents(), i = 0; i < parents.length && !(isFixed = "fixed" == $(parents[i]).css("position")); i++) ;
                    var originWidth = origin.outerWidth(), originHeight = origin.outerHeight(), originTop = isFixed ? origin.offset().top - $(document).scrollTop() : origin.offset().top, originLeft = isFixed ? origin.offset().left - $(document).scrollLeft() : origin.offset().left, windowWidth = $(window).width(), windowHeight = $(window).height(), centerX = windowWidth / 2, centerY = windowHeight / 2, isLeft = originLeft <= centerX, isRight = centerX < originLeft, isTop = originTop <= centerY, isBottom = centerY < originTop, isCenterX = .25 * windowWidth <= originLeft && originLeft <= .75 * windowWidth, tapTargetWidth = tapTargetEl.outerWidth(), tapTargetHeight = tapTargetEl.outerHeight(), tapTargetTop = originTop + originHeight / 2 - tapTargetHeight / 2, tapTargetLeft = originLeft + originWidth / 2 - tapTargetWidth / 2, tapTargetPosition = isFixed ? "fixed" : "absolute", tapTargetTextWidth = isCenterX ? tapTargetWidth : tapTargetWidth / 2 + originWidth, tapTargetTextHeight = tapTargetHeight / 2, tapTargetTextTop = isTop ? tapTargetHeight / 2 : 0, tapTargetTextLeft = isLeft && !isCenterX ? tapTargetWidth / 2 - originWidth : 0, tapTargetTextPadding = originWidth, tapTargetTextAlign = isBottom ? "bottom" : "top", tapTargetWaveWidth = 2 * originWidth, tapTargetWaveHeight = tapTargetWaveWidth, tapTargetWaveTop = tapTargetHeight / 2 - tapTargetWaveHeight / 2, tapTargetWaveLeft = tapTargetWidth / 2 - tapTargetWaveWidth / 2, tapTargetWrapperCssObj = {};
                    tapTargetWrapperCssObj.top = isTop ? tapTargetTop : "", tapTargetWrapperCssObj.right = isRight ? windowWidth - tapTargetLeft - tapTargetWidth : "", 
                    tapTargetWrapperCssObj.bottom = isBottom ? windowHeight - tapTargetTop - tapTargetHeight : "", 
                    tapTargetWrapperCssObj.left = isLeft ? tapTargetLeft : "", tapTargetWrapperCssObj.position = tapTargetPosition, 
                    tapTargetWrapper.css(tapTargetWrapperCssObj), tapTargetContentEl.css({
                        width: tapTargetTextWidth,
                        height: tapTargetTextHeight,
                        top: tapTargetTextTop,
                        right: 0,
                        bottom: 0,
                        left: tapTargetTextLeft,
                        padding: tapTargetTextPadding,
                        verticalAlign: tapTargetTextAlign
                    }), tapTargetWave.css({
                        top: tapTargetWaveTop,
                        left: tapTargetWaveLeft,
                        width: tapTargetWaveWidth,
                        height: tapTargetWaveHeight
                    });
                };
                "open" == options && (calculateTapTarget(), tapTargetWrapper.is(".open") || (tapTargetWrapper.addClass("open"), 
                setTimeout(function() {
                    tapTargetOriginEl.off("click.tapTarget").on("click.tapTarget", function(e) {
                        closeTapTarget(), tapTargetOriginEl.off("click.tapTarget");
                    }), $(document).off("click.tapTarget").on("click.tapTarget", function(e) {
                        closeTapTarget(), $(document).off("click.tapTarget");
                    });
                    var throttledCalc = Materialize.throttle(function() {
                        calculateTapTarget();
                    }, 200);
                    $(window).off("resize.tapTarget").on("resize.tapTarget", throttledCalc);
                }, 0))), "close" == options && closeTapTarget();
            });
        },
        open: function() {},
        close: function() {}
    };
    $.fn.tapTarget = function(methodOrOptions) {
        if (methods[methodOrOptions] || "object" == typeof methodOrOptions) return methods.init.apply(this, arguments);
        $.error("Method " + methodOrOptions + " does not exist on jQuery.tap-target");
    };
}(jQuery), function($, Vel) {
    "use strict";
    var _defaults = {
        displayLength: 1 / 0,
        inDuration: 300,
        outDuration: 375,
        className: void 0,
        completeCallback: void 0,
        activationPercent: .8
    }, Toast = function() {
        function Toast(message, displayLength, className, completeCallback) {
            if (_classCallCheck(this, Toast), message) {
                this.options = {
                    displayLength: displayLength,
                    className: className,
                    completeCallback: completeCallback
                }, this.options = $.extend({}, Toast.defaults, this.options), this.message = message, 
                this.panning = !1, this.timeRemaining = this.options.displayLength, 0 === Toast._toasts.length && Toast._createContainer(), 
                Toast._toasts.push(this);
                var toastElement = this.createToast();
                (toastElement.M_Toast = this).el = toastElement, this._animateIn(), this.setTimer();
            }
        }
        return _createClass(Toast, [ {
            key: "createToast",
            value: function() {
                var toast = document.createElement("div");
                if (toast.classList.add("toast"), this.options.className) {
                    var count, classes = this.options.className.split(" "), i = void 0;
                    for (i = 0, count = classes.length; i < count; i++) toast.classList.add(classes[i]);
                }
                return ("object" == typeof HTMLElement ? this.message instanceof HTMLElement : this.message && "object" == typeof this.message && null !== this.message && 1 === this.message.nodeType && "string" == typeof this.message.nodeName) ? toast.appendChild(this.message) : this.message instanceof jQuery ? $(toast).append(this.message) : toast.innerHTML = this.message, 
                Toast._container.appendChild(toast), toast;
            }
        }, {
            key: "_animateIn",
            value: function() {
                Vel(this.el, {
                    top: 0,
                    opacity: 1
                }, {
                    duration: 300,
                    easing: "easeOutCubic",
                    queue: !1
                });
            }
        }, {
            key: "setTimer",
            value: function() {
                var _this3 = this;
                this.timeRemaining !== 1 / 0 && (this.counterInterval = setInterval(function() {
                    _this3.panning || (_this3.timeRemaining -= 20), _this3.timeRemaining <= 0 && _this3.remove();
                }, 20));
            }
        }, {
            key: "remove",
            value: function() {
                var _this4 = this;
                window.clearInterval(this.counterInterval);
                var activationDistance = this.el.offsetWidth * this.options.activationPercent;
                this.wasSwiped && (this.el.style.transition = "transform .05s, opacity .05s", this.el.style.transform = "translateX(" + activationDistance + "px)", 
                this.el.style.opacity = 0), Vel(this.el, {
                    opacity: 0,
                    marginTop: "-40px"
                }, {
                    duration: this.options.outDuration,
                    easing: "easeOutExpo",
                    queue: !1,
                    complete: function() {
                        "function" == typeof _this4.options.completeCallback && _this4.options.completeCallback(), 
                        _this4.el.parentNode.removeChild(_this4.el), Toast._toasts.splice(Toast._toasts.indexOf(_this4), 1), 
                        0 === Toast._toasts.length && Toast._removeContainer();
                    }
                });
            }
        } ], [ {
            key: "_createContainer",
            value: function() {
                var container = document.createElement("div");
                container.setAttribute("id", "toast-container"), container.addEventListener("touchstart", Toast._onDragStart), 
                container.addEventListener("touchmove", Toast._onDragMove), container.addEventListener("touchend", Toast._onDragEnd), 
                container.addEventListener("mousedown", Toast._onDragStart), document.addEventListener("mousemove", Toast._onDragMove), 
                document.addEventListener("mouseup", Toast._onDragEnd), document.body.appendChild(container), 
                Toast._container = container;
            }
        }, {
            key: "_removeContainer",
            value: function() {
                document.removeEventListener("mousemove", Toast._onDragMove), document.removeEventListener("mouseup", Toast._onDragEnd), 
                Toast._container.parentNode.removeChild(Toast._container), Toast._container = null;
            }
        }, {
            key: "_onDragStart",
            value: function(e) {
                if (e.target && $(e.target).closest(".toast").length) {
                    var toast = $(e.target).closest(".toast")[0].M_Toast;
                    toast.panning = !0, (Toast._draggedToast = toast).el.classList.add("panning"), toast.el.style.transition = "", 
                    toast.startingXPos = Toast._xPos(e), toast.time = Date.now(), toast.xPos = Toast._xPos(e);
                }
            }
        }, {
            key: "_onDragMove",
            value: function(e) {
                if (Toast._draggedToast) {
                    e.preventDefault();
                    var toast = Toast._draggedToast;
                    toast.deltaX = Math.abs(toast.xPos - Toast._xPos(e)), toast.xPos = Toast._xPos(e), 
                    toast.velocityX = toast.deltaX / (Date.now() - toast.time), toast.time = Date.now();
                    var totalDeltaX = toast.xPos - toast.startingXPos, activationDistance = toast.el.offsetWidth * toast.options.activationPercent;
                    toast.el.style.transform = "translateX(" + totalDeltaX + "px)", toast.el.style.opacity = 1 - Math.abs(totalDeltaX / activationDistance);
                }
            }
        }, {
            key: "_onDragEnd",
            value: function(e) {
                if (Toast._draggedToast) {
                    var toast = Toast._draggedToast;
                    toast.panning = !1, toast.el.classList.remove("panning");
                    var totalDeltaX = toast.xPos - toast.startingXPos, activationDistance = toast.el.offsetWidth * toast.options.activationPercent;
                    Math.abs(totalDeltaX) > activationDistance || 1 < toast.velocityX ? (toast.wasSwiped = !0, 
                    toast.remove()) : (toast.el.style.transition = "transform .2s, opacity .2s", toast.el.style.transform = "", 
                    toast.el.style.opacity = ""), Toast._draggedToast = null;
                }
            }
        }, {
            key: "_xPos",
            value: function(e) {
                return e.targetTouches && 1 <= e.targetTouches.length ? e.targetTouches[0].clientX : e.clientX;
            }
        }, {
            key: "removeAll",
            value: function() {
                for (var toastIndex in Toast._toasts) Toast._toasts[toastIndex].remove();
            }
        }, {
            key: "defaults",
            get: function() {
                return _defaults;
            }
        } ]), Toast;
    }();
    Toast._toasts = [], Toast._container = null, Toast._draggedToast = null, Materialize.Toast = Toast, 
    Materialize.toast = function(message, displayLength, className, completeCallback) {
        return new Toast(message, displayLength, className, completeCallback);
    };
}(jQuery, Materialize.Vel), function($) {
    $.fn.tooltip = function(options) {
        return "remove" === options ? (this.each(function() {
            $("#" + $(this).attr("data-tooltip-id")).remove(), $(this).removeAttr("data-tooltip-id"), 
            $(this).off("mouseenter.tooltip mouseleave.tooltip");
        }), !1) : (options = $.extend({
            delay: 350,
            tooltip: "",
            position: "bottom",
            html: !1
        }, options), this.each(function() {
            var allowHtml, tooltipDelay, tooltipPosition, tooltipText, tooltipEl, backdrop, tooltipId = Materialize.guid(), origin = $(this);
            origin.attr("data-tooltip-id") && $("#" + origin.attr("data-tooltip-id")).remove(), 
            origin.attr("data-tooltip-id", tooltipId);
            var setAttributes = function() {
                allowHtml = origin.attr("data-html") ? "true" === origin.attr("data-html") : options.html, 
                tooltipDelay = void 0 === (tooltipDelay = origin.attr("data-delay")) || "" === tooltipDelay ? options.delay : tooltipDelay, 
                tooltipPosition = void 0 === (tooltipPosition = origin.attr("data-position")) || "" === tooltipPosition ? options.position : tooltipPosition, 
                tooltipText = void 0 === (tooltipText = origin.attr("data-tooltip")) || "" === tooltipText ? options.tooltip : tooltipText;
            };
            setAttributes();
            var tooltip;
            tooltip = $('<div class="material-tooltip"></div>'), tooltipText = allowHtml ? $("<span></span>").html(tooltipText) : $("<span></span>").text(tooltipText), 
            tooltip.append(tooltipText).appendTo($("body")).attr("id", tooltipId), (backdrop = $('<div class="backdrop"></div>')).appendTo(tooltip), 
            tooltipEl = tooltip, origin.off("mouseenter.tooltip mouseleave.tooltip");
            var timeoutRef, started = !1;
            origin.on({
                "mouseenter.tooltip": function(e) {
                    timeoutRef = setTimeout(function() {
                        setAttributes(), started = !0, tooltipEl.velocity("stop"), backdrop.velocity("stop"), 
                        tooltipEl.css({
                            visibility: "visible",
                            left: "0px",
                            top: "0px"
                        });
                        var scaleXFactor, scaleYFactor, scaleFactor, targetTop, targetLeft, newCoordinates, originWidth = origin.outerWidth(), originHeight = origin.outerHeight(), tooltipHeight = tooltipEl.outerHeight(), tooltipWidth = tooltipEl.outerWidth(), tooltipVerticalMovement = "0px", tooltipHorizontalMovement = "0px", backdropOffsetWidth = backdrop[0].offsetWidth, backdropOffsetHeight = backdrop[0].offsetHeight;
                        "top" === tooltipPosition ? (targetTop = origin.offset().top - tooltipHeight - 5, 
                        targetLeft = origin.offset().left + originWidth / 2 - tooltipWidth / 2, newCoordinates = repositionWithinScreen(targetLeft, targetTop, tooltipWidth, tooltipHeight), 
                        tooltipVerticalMovement = "-10px", backdrop.css({
                            bottom: 0,
                            left: 0,
                            borderRadius: "14px 14px 0 0",
                            transformOrigin: "50% 100%",
                            marginTop: tooltipHeight,
                            marginLeft: tooltipWidth / 2 - backdropOffsetWidth / 2
                        })) : "left" === tooltipPosition ? (targetTop = origin.offset().top + originHeight / 2 - tooltipHeight / 2, 
                        targetLeft = origin.offset().left - tooltipWidth - 5, newCoordinates = repositionWithinScreen(targetLeft, targetTop, tooltipWidth, tooltipHeight), 
                        tooltipHorizontalMovement = "-10px", backdrop.css({
                            top: "-7px",
                            right: 0,
                            width: "14px",
                            height: "14px",
                            borderRadius: "14px 0 0 14px",
                            transformOrigin: "95% 50%",
                            marginTop: tooltipHeight / 2,
                            marginLeft: tooltipWidth
                        })) : "right" === tooltipPosition ? (targetTop = origin.offset().top + originHeight / 2 - tooltipHeight / 2, 
                        targetLeft = origin.offset().left + originWidth + 5, newCoordinates = repositionWithinScreen(targetLeft, targetTop, tooltipWidth, tooltipHeight), 
                        tooltipHorizontalMovement = "+10px", backdrop.css({
                            top: "-7px",
                            left: 0,
                            width: "14px",
                            height: "14px",
                            borderRadius: "0 14px 14px 0",
                            transformOrigin: "5% 50%",
                            marginTop: tooltipHeight / 2,
                            marginLeft: "0px"
                        })) : (targetTop = origin.offset().top + origin.outerHeight() + 5, targetLeft = origin.offset().left + originWidth / 2 - tooltipWidth / 2, 
                        newCoordinates = repositionWithinScreen(targetLeft, targetTop, tooltipWidth, tooltipHeight), 
                        tooltipVerticalMovement = "+10px", backdrop.css({
                            top: 0,
                            left: 0,
                            marginLeft: tooltipWidth / 2 - backdropOffsetWidth / 2
                        })), tooltipEl.css({
                            top: newCoordinates.y,
                            left: newCoordinates.x
                        }), scaleXFactor = Math.SQRT2 * tooltipWidth / parseInt(backdropOffsetWidth), scaleYFactor = Math.SQRT2 * tooltipHeight / parseInt(backdropOffsetHeight), 
                        scaleFactor = Math.max(scaleXFactor, scaleYFactor), tooltipEl.velocity({
                            translateY: tooltipVerticalMovement,
                            translateX: tooltipHorizontalMovement
                        }, {
                            duration: 350,
                            queue: !1
                        }).velocity({
                            opacity: 1
                        }, {
                            duration: 300,
                            delay: 50,
                            queue: !1
                        }), backdrop.css({
                            visibility: "visible"
                        }).velocity({
                            opacity: 1
                        }, {
                            duration: 55,
                            delay: 0,
                            queue: !1
                        }).velocity({
                            scaleX: scaleFactor,
                            scaleY: scaleFactor
                        }, {
                            duration: 300,
                            delay: 0,
                            queue: !1,
                            easing: "easeInOutQuad"
                        });
                    }, tooltipDelay);
                },
                "mouseleave.tooltip": function() {
                    started = !1, clearTimeout(timeoutRef), setTimeout(function() {
                        !0 !== started && (tooltipEl.velocity({
                            opacity: 0,
                            translateY: 0,
                            translateX: 0
                        }, {
                            duration: 225,
                            queue: !1
                        }), backdrop.velocity({
                            opacity: 0,
                            scaleX: 1,
                            scaleY: 1
                        }, {
                            duration: 225,
                            queue: !1,
                            complete: function() {
                                backdrop.css({
                                    visibility: "hidden"
                                }), tooltipEl.css({
                                    visibility: "hidden"
                                }), started = !1;
                            }
                        }));
                    }, 225);
                }
            });
        }));
    };
    var repositionWithinScreen = function(x, y, width, height) {
        var newX = x, newY = y;
        return newX < 0 ? newX = 4 : newX + width > window.innerWidth && (newX -= newX + width - window.innerWidth), 
        newY < 0 ? newY = 4 : newY + height > window.innerHeight + $(window).scrollTop && (newY -= newY + height - window.innerHeight), 
        {
            x: newX,
            y: newY
        };
    };
    $(document).ready(function() {
        $(".tooltipped").tooltip();
    });
}(jQuery), function($) {
    Materialize.fadeInImage = function(selectorOrEl) {
        var element;
        if ("string" == typeof selectorOrEl) element = $(selectorOrEl); else {
            if ("object" != typeof selectorOrEl) return;
            element = selectorOrEl;
        }
        element.css({
            opacity: 0
        }), $(element).velocity({
            opacity: 1
        }, {
            duration: 650,
            queue: !1,
            easing: "easeOutSine"
        }), $(element).velocity({
            opacity: 1
        }, {
            duration: 1300,
            queue: !1,
            easing: "swing",
            step: function(now, fx) {
                var grayscale_setting = now / (fx.start = 100), brightness_setting = 150 - (100 - now) / 1.75;
                brightness_setting < 100 && (brightness_setting = 100), 0 <= now && $(this).css({
                    "-webkit-filter": "grayscale(" + grayscale_setting + ")brightness(" + brightness_setting + "%)",
                    filter: "grayscale(" + grayscale_setting + ")brightness(" + brightness_setting + "%)"
                });
            }
        });
    }, Materialize.showStaggeredList = function(selectorOrEl) {
        var element;
        if ("string" == typeof selectorOrEl) element = $(selectorOrEl); else {
            if ("object" != typeof selectorOrEl) return;
            element = selectorOrEl;
        }
        var time = 0;
        element.find("li").velocity({
            translateX: "-100px"
        }, {
            duration: 0
        }), element.find("li").each(function() {
            $(this).velocity({
                opacity: "1",
                translateX: "0"
            }, {
                duration: 800,
                delay: time,
                easing: [ 60, 10 ]
            }), time += 120;
        });
    }, $(document).ready(function() {
        var swipeLeft = !1, swipeRight = !1;
        $(".dismissable").each(function() {
            $(this).hammer({
                prevent_default: !1
            }).on("pan", function(e) {
                if ("touch" === e.gesture.pointerType) {
                    var $this = $(this), direction = e.gesture.direction, x = e.gesture.deltaX, velocityX = e.gesture.velocityX;
                    $this.velocity({
                        translateX: x
                    }, {
                        duration: 50,
                        queue: !1,
                        easing: "easeOutQuad"
                    }), 4 === direction && (x > $this.innerWidth() / 2 || velocityX < -.75) && (swipeLeft = !0), 
                    2 === direction && (x < -1 * $this.innerWidth() / 2 || .75 < velocityX) && (swipeRight = !0);
                }
            }).on("panend", function(e) {
                if (Math.abs(e.gesture.deltaX) < $(this).innerWidth() / 2 && (swipeLeft = swipeRight = !1), 
                "touch" === e.gesture.pointerType) {
                    var fullWidth, $this = $(this);
                    if (swipeLeft || swipeRight) fullWidth = swipeLeft ? $this.innerWidth() : -1 * $this.innerWidth(), 
                    $this.velocity({
                        translateX: fullWidth
                    }, {
                        duration: 100,
                        queue: !1,
                        easing: "easeOutQuad",
                        complete: function() {
                            $this.css("border", "none"), $this.velocity({
                                height: 0,
                                padding: 0
                            }, {
                                duration: 200,
                                queue: !1,
                                easing: "easeOutQuad",
                                complete: function() {
                                    $this.remove();
                                }
                            });
                        }
                    }); else $this.velocity({
                        translateX: 0
                    }, {
                        duration: 100,
                        queue: !1,
                        easing: "easeOutQuad"
                    });
                    swipeRight = swipeLeft = !1;
                }
            });
        });
    });
}(jQuery), function(window) {
    "use strict";
    var Waves = Waves || {}, $$ = document.querySelectorAll.bind(document);
    function convertStyle(obj) {
        var style = "";
        for (var a in obj) obj.hasOwnProperty(a) && (style += a + ":" + obj[a] + ";");
        return style;
    }
    var Effect = {
        duration: 750,
        show: function(e, element) {
            if (2 === e.button) return !1;
            var el = element || this, ripple = document.createElement("div");
            ripple.className = "waves-ripple", el.appendChild(ripple);
            var elem, docElem, win, box, doc, pos = (box = {
                top: 0,
                left: 0
            }, doc = (elem = el) && elem.ownerDocument, docElem = doc.documentElement, void 0 !== elem.getBoundingClientRect && (box = elem.getBoundingClientRect()), 
            win = function(elem) {
                return null !== (obj = elem) && obj === obj.window ? elem : 9 === elem.nodeType && elem.defaultView;
                var obj;
            }(doc), {
                top: box.top + win.pageYOffset - docElem.clientTop,
                left: box.left + win.pageXOffset - docElem.clientLeft
            }), relativeY = e.pageY - pos.top, relativeX = e.pageX - pos.left, scale = "scale(" + el.clientWidth / 100 * 10 + ")";
            "touches" in e && (relativeY = e.touches[0].pageY - pos.top, relativeX = e.touches[0].pageX - pos.left), 
            ripple.setAttribute("data-hold", Date.now()), ripple.setAttribute("data-scale", scale), 
            ripple.setAttribute("data-x", relativeX), ripple.setAttribute("data-y", relativeY);
            var rippleStyle = {
                top: relativeY + "px",
                left: relativeX + "px"
            };
            ripple.className = ripple.className + " waves-notransition", ripple.setAttribute("style", convertStyle(rippleStyle)), 
            ripple.className = ripple.className.replace("waves-notransition", ""), rippleStyle["-webkit-transform"] = scale, 
            rippleStyle["-moz-transform"] = scale, rippleStyle["-ms-transform"] = scale, rippleStyle["-o-transform"] = scale, 
            rippleStyle.transform = scale, rippleStyle.opacity = "1", rippleStyle["-webkit-transition-duration"] = Effect.duration + "ms", 
            rippleStyle["-moz-transition-duration"] = Effect.duration + "ms", rippleStyle["-o-transition-duration"] = Effect.duration + "ms", 
            rippleStyle["transition-duration"] = Effect.duration + "ms", rippleStyle["-webkit-transition-timing-function"] = "cubic-bezier(0.250, 0.460, 0.450, 0.940)", 
            rippleStyle["-moz-transition-timing-function"] = "cubic-bezier(0.250, 0.460, 0.450, 0.940)", 
            rippleStyle["-o-transition-timing-function"] = "cubic-bezier(0.250, 0.460, 0.450, 0.940)", 
            rippleStyle["transition-timing-function"] = "cubic-bezier(0.250, 0.460, 0.450, 0.940)", 
            ripple.setAttribute("style", convertStyle(rippleStyle));
        },
        hide: function(e) {
            TouchHandler.touchup(e);
            var el = this, ripple = (el.clientWidth, null), ripples = el.getElementsByClassName("waves-ripple");
            if (!(0 < ripples.length)) return !1;
            var relativeX = (ripple = ripples[ripples.length - 1]).getAttribute("data-x"), relativeY = ripple.getAttribute("data-y"), scale = ripple.getAttribute("data-scale"), delay = 350 - (Date.now() - Number(ripple.getAttribute("data-hold")));
            delay < 0 && (delay = 0), setTimeout(function() {
                var style = {
                    top: relativeY + "px",
                    left: relativeX + "px",
                    opacity: "0",
                    "-webkit-transition-duration": Effect.duration + "ms",
                    "-moz-transition-duration": Effect.duration + "ms",
                    "-o-transition-duration": Effect.duration + "ms",
                    "transition-duration": Effect.duration + "ms",
                    "-webkit-transform": scale,
                    "-moz-transform": scale,
                    "-ms-transform": scale,
                    "-o-transform": scale,
                    transform: scale
                };
                ripple.setAttribute("style", convertStyle(style)), setTimeout(function() {
                    try {
                        el.removeChild(ripple);
                    } catch (e) {
                        return !1;
                    }
                }, Effect.duration);
            }, delay);
        },
        wrapInput: function(elements) {
            for (var a = 0; a < elements.length; a++) {
                var el = elements[a];
                if ("input" === el.tagName.toLowerCase()) {
                    var parent = el.parentNode;
                    if ("i" === parent.tagName.toLowerCase() && -1 !== parent.className.indexOf("waves-effect")) continue;
                    var wrapper = document.createElement("i");
                    wrapper.className = el.className + " waves-input-wrapper";
                    var elementStyle = el.getAttribute("style");
                    elementStyle || (elementStyle = ""), wrapper.setAttribute("style", elementStyle), 
                    el.className = "waves-button-input", el.removeAttribute("style"), parent.replaceChild(wrapper, el), 
                    wrapper.appendChild(el);
                }
            }
        }
    }, TouchHandler = {
        touches: 0,
        allowEvent: function(e) {
            var allow = !0;
            return "touchstart" === e.type ? TouchHandler.touches += 1 : "touchend" === e.type || "touchcancel" === e.type ? setTimeout(function() {
                0 < TouchHandler.touches && (TouchHandler.touches -= 1);
            }, 500) : "mousedown" === e.type && 0 < TouchHandler.touches && (allow = !1), allow;
        },
        touchup: function(e) {
            TouchHandler.allowEvent(e);
        }
    };
    function showEffect(e) {
        var element = function(e) {
            if (!1 === TouchHandler.allowEvent(e)) return null;
            for (var element = null, target = e.target || e.srcElement; null !== target.parentNode; ) {
                if (!(target instanceof SVGElement) && -1 !== target.className.indexOf("waves-effect")) {
                    element = target;
                    break;
                }
                target = target.parentNode;
            }
            return element;
        }(e);
        null !== element && (Effect.show(e, element), "ontouchstart" in window && (element.addEventListener("touchend", Effect.hide, !1), 
        element.addEventListener("touchcancel", Effect.hide, !1)), element.addEventListener("mouseup", Effect.hide, !1), 
        element.addEventListener("mouseleave", Effect.hide, !1), element.addEventListener("dragend", Effect.hide, !1));
    }
    Waves.displayEffect = function(options) {
        "duration" in (options = options || {}) && (Effect.duration = options.duration), 
        Effect.wrapInput($$(".waves-effect")), "ontouchstart" in window && document.body.addEventListener("touchstart", showEffect, !1), 
        document.body.addEventListener("mousedown", showEffect, !1);
    }, Waves.attach = function(element) {
        "input" === element.tagName.toLowerCase() && (Effect.wrapInput([ element ]), element = element.parentNode), 
        "ontouchstart" in window && element.addEventListener("touchstart", showEffect, !1), 
        element.addEventListener("mousedown", showEffect, !1);
    }, window.Waves = Waves, document.addEventListener("DOMContentLoaded", function() {
        Waves.displayEffect();
    }, !1);
}(window);
//# sourceMappingURL=gohstats.min.js.map
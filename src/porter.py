"""
Porter stemming algorithm (M.F. Porter, 1980).

A faithful implementation of the classic suffix-stripping algorithm used to
reduce inflected words to a common root (e.g. "chocolate", "chocolates" ->
"chocol"). The implementation follows Porter's original reference algorithm and
requires no third-party dependencies.
"""


class PorterStemmer:
    def __init__(self):
        # b   -> buffer holding the word being stemmed
        # k   -> index of the last letter of the word in the buffer
        # k0  -> index of the first letter (always 0)
        # j   -> working pointer used by the individual steps
        self.b = ""
        self.k = 0
        self.k0 = 0
        self.j = 0

    def cons(self, i):
        """Return True if b[i] is a consonant."""
        if self.b[i] in "aeiou":
            return False
        if self.b[i] == 'y':
            if i == self.k0:
                return True
            else:
                return not self.cons(i - 1)
        return True

    def m(self):
        """Count the vowel-consonant sequences (the measure 'm') between k0 and j."""
        n = 0
        i = self.k0
        while True:
            if i > self.j:
                return n
            if not self.cons(i):
                break
            i = i + 1
        i = i + 1
        while True:
            while True:
                if i > self.j:
                    return n
                if self.cons(i):
                    break
                i = i + 1
            i = i + 1
            n = n + 1
            while True:
                if i > self.j:
                    return n
                if not self.cons(i):
                    break
                i = i + 1
            i = i + 1

    def vowelinstem(self):
        """Return True if k0..j contains at least one vowel."""
        for i in range(self.k0, self.j + 1):
            if not self.cons(i):
                return True
        return False

    def doublec(self, j):
        """Return True if b[j-1..j] is a double consonant."""
        if j < (self.k0 + 1):
            return False
        if self.b[j] != self.b[j - 1]:
            return False
        return self.cons(j)

    def cvc(self, i):
        """
        Return True if i-2, i-1, i form a consonant-vowel-consonant sequence and
        the final consonant is not w, x or y. Used when restoring a trailing 'e'.
        """
        if i < (self.k0 + 2) or not self.cons(i) or self.cons(i - 1) or not self.cons(i - 2):
            return False
        ch = self.b[i]
        if ch in "wxy":
            return False
        return True

    def ends(self, s):
        """Return True if k0..k ends with the string s."""
        length = len(s)
        if s[length - 1] != self.b[self.k]:
            return False
        if length > (self.k - self.k0 + 1):
            return False
        if self.b[self.k - length + 1:self.k + 1] != s:
            return False
        self.j = self.k - length
        return True

    def setto(self, s):
        """Replace (j+1)..k with the string s and adjust k."""
        length = len(s)
        self.b = self.b[:self.j + 1] + s + self.b[self.j + length + 1:]
        self.k = self.j + length

    def r(self, s):
        """Apply setto(s) only when the measure m() > 0."""
        if self.m() > 0:
            self.setto(s)

    def step1ab(self):
        """Remove plurals and -ed/-ing suffixes."""
        if self.b[self.k] == 's':
            if self.ends("sses"):
                self.k = self.k - 2
            elif self.ends("ies"):
                self.setto("i")
            elif self.b[self.k - 1] != 's':
                self.k = self.k - 1
        if self.ends("eed"):
            if self.m() > 0:
                self.k = self.k - 1
        elif (self.ends("ed") or self.ends("ing")) and self.vowelinstem():
            self.k = self.j
            if self.ends("at"):
                self.setto("ate")
            elif self.ends("bl"):
                self.setto("ble")
            elif self.ends("iz"):
                self.setto("ize")
            elif self.doublec(self.k):
                self.k = self.k - 1
                ch = self.b[self.k]
                if ch == 'l' or ch == 's' or ch == 'z':
                    self.k = self.k + 1
            elif self.m() == 1 and self.cvc(self.k):
                self.setto("e")

    def step1c(self):
        """Turn a trailing -y into -i when the stem contains a vowel."""
        if self.ends("y") and self.vowelinstem():
            self.b = self.b[:self.k] + 'i' + self.b[self.k + 1:]

    def step2(self):
        """Map double suffixes to single ones (measure m > 0)."""
        if self.b[self.k - 1] == 'a':
            if self.ends("ational"):
                self.r("ate")
            elif self.ends("tional"):
                self.r("tion")
        elif self.b[self.k - 1] == 'c':
            if self.ends("enci"):
                self.r("ence")
            elif self.ends("anci"):
                self.r("ance")
        elif self.b[self.k - 1] == 'e':
            if self.ends("izer"):
                self.r("ize")
        elif self.b[self.k - 1] == 'l':
            if self.ends("bli"):
                self.r("ble")
            elif self.ends("alli"):
                self.r("al")
            elif self.ends("entli"):
                self.r("ent")
            elif self.ends("eli"):
                self.r("e")
            elif self.ends("ousli"):
                self.r("ous")
        elif self.b[self.k - 1] == 'o':
            if self.ends("ization"):
                self.r("ize")
            elif self.ends("ation"):
                self.r("ate")
            elif self.ends("ator"):
                self.r("ate")
        elif self.b[self.k - 1] == 's':
            if self.ends("alism"):
                self.r("al")
            elif self.ends("iveness"):
                self.r("ive")
            elif self.ends("fulness"):
                self.r("ful")
            elif self.ends("ousness"):
                self.r("ous")
        elif self.b[self.k - 1] == 't':
            if self.ends("aliti"):
                self.r("al")
            elif self.ends("iviti"):
                self.r("ive")
            elif self.ends("biliti"):
                self.r("ble")
        elif self.b[self.k - 1] == 'g':
            if self.ends("logi"):
                self.r("log")

    def step3(self):
        """Remove -ic-, -full, -ness and similar suffixes (measure m > 0)."""
        if self.b[self.k] == 'e':
            if self.ends("icate"):
                self.r("ic")
            elif self.ends("ative"):
                self.r("")
            elif self.ends("alize"):
                self.r("al")
        elif self.b[self.k] == 'i':
            if self.ends("iciti"):
                self.r("ic")
        elif self.b[self.k] == 'l':
            if self.ends("ical"):
                self.r("ic")
            elif self.ends("ful"):
                self.r("")
        elif self.b[self.k] == 's':
            if self.ends("ness"):
                self.r("")

    def step4(self):
        """Remove suffixes -ant, -ence, ... when the measure m > 1."""
        if self.b[self.k - 1] == 'a':
            if self.ends("al"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'c':
            if self.ends("ance"):
                pass
            elif self.ends("ence"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'e':
            if self.ends("er"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'i':
            if self.ends("ic"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'l':
            if self.ends("able"):
                pass
            elif self.ends("ible"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'n':
            if self.ends("ant"):
                pass
            elif self.ends("ement"):
                pass
            elif self.ends("ment"):
                pass
            elif self.ends("ent"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'o':
            if self.ends("ion") and (self.b[self.j] == 's' or self.b[self.j] == 't'):
                pass
            elif self.ends("ou"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 's':
            if self.ends("ism"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 't':
            if self.ends("ate"):
                pass
            elif self.ends("iti"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'u':
            if self.ends("ous"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'v':
            if self.ends("ive"):
                pass
            else:
                return
        elif self.b[self.k - 1] == 'z':
            if self.ends("ize"):
                pass
            else:
                return
        else:
            return
        if self.m() > 1:
            self.k = self.j

    def step5(self):
        """Remove a trailing -e and reduce a double -ll (measure m > 1)."""
        self.j = self.k
        if self.b[self.k] == 'e':
            a = self.m()
            if a > 1 or (a == 1 and not self.cvc(self.k - 1)):
                self.k = self.k - 1
        if self.b[self.k] == 'l' and self.doublec(self.k) and self.m() > 1:
            self.k = self.k - 1

    def stem(self, word):
        """Return the stem of the given word (expected to be lowercase)."""
        word = word.lower()
        # Words of one or two letters are returned unchanged.
        if len(word) <= 2:
            return word
        self.b = word
        self.k = len(word) - 1
        self.k0 = 0
        self.step1ab()
        self.step1c()
        self.step2()
        self.step3()
        self.step4()
        self.step5()
        return self.b[self.k0:self.k + 1]


# Shared instance for reuse (the stemmer keeps no state between calls).
_stemmer = PorterStemmer()


def stem(word):
    return _stemmer.stem(word)

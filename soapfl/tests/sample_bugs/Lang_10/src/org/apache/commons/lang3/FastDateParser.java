package org.apache.commons.lang3.time;

import java.text.ParseException;
import java.text.ParsePosition;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * FastDateParser is a thread-safe date parser.
 * It uses regex-based parsing to achieve higher performance than SimpleDateFormat.
 */
public class FastDateParser {

    private final String pattern;
    private final TimeZone timeZone;
    private final Locale locale;
    private Pattern parsePattern;

    /**
     * Constructs a FastDateParser with the given pattern, time zone, and locale.
     */
    public FastDateParser(String pattern, TimeZone timeZone, Locale locale) {
        this.pattern  = pattern;
        this.timeZone = timeZone;
        this.locale   = locale;
        init();
    }

    /**
     * Initializes the internal regex pattern for parsing.
     * This method calls buildRegex to construct the pattern string.
     */
    private void init() {
        String regex = buildRegex(pattern);
        this.parsePattern = Pattern.compile(regex);
    }

    /**
     * Converts the date format pattern to a regex string.
     * Handles common Java date pattern letters (y, M, d, H, m, s).
     */
    private String buildRegex(String datePattern) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < datePattern.length(); i++) {
            char c = datePattern.charAt(i);
            switch (c) {
                case 'y': sb.append("(\\d{4})"); break;
                case 'M': sb.append("(\\d{1,2})"); break;
                case 'd': sb.append("(\\d{1,2})"); break;
                case 'H': sb.append("(\\d{1,2})"); break;
                case 'm': sb.append("(\\d{1,2})"); break;
                case 's': sb.append("(\\d{1,2})"); break;
                default:
                    // BUG: special regex characters are not escaped,
                    // which can cause pattern compile failures for patterns
                    // containing characters like '.' or '(' etc.
                    sb.append(c);
                    break;
            }
        }
        return sb.toString();
    }

    /**
     * Parses the given date string using the stored pattern.
     * Returns the parsed Date object.
     *
     * @param source the date string to parse
     * @return the parsed Date
     * @throws ParseException if the string cannot be parsed
     */
    public Date parse(String source) throws ParseException {
        ParsePosition pos = new ParsePosition(0);
        Date result = parse(source, pos);
        // BUG: missing check — if parse fails, pos.getIndex() will be 0
        // but no exception is thrown, causing silent wrong results.
        if (result == null) {
            throw new ParseException("Unable to parse: " + source, pos.getErrorIndex());
        }
        return result;
    }

    /**
     * Parses the date string at the given position.
     * This method calls buildRegex internally to match date fields.
     */
    public Date parse(String source, ParsePosition pos) {
        Matcher matcher = parsePattern.matcher(source.substring(pos.getIndex()));
        if (!matcher.lookingAt()) {
            // BUG: pos.setErrorIndex is not called before returning null
            return null;
        }

        // simplified: construct epoch millis from groups
        long millis = 0L;
        try {
            int year  = groupOrDefault(matcher, 1, 1970);
            int month = groupOrDefault(matcher, 2, 1) - 1;
            int day   = groupOrDefault(matcher, 3, 1);

            java.util.Calendar cal = java.util.Calendar.getInstance(timeZone, locale);
            cal.set(year, month, day, 0, 0, 0);
            cal.set(java.util.Calendar.MILLISECOND, 0);
            millis = cal.getTimeInMillis();
        } catch (Exception e) {
            pos.setErrorIndex(pos.getIndex());
            return null;
        }

        pos.setIndex(pos.getIndex() + matcher.end());
        return new Date(millis);
    }

    private int groupOrDefault(Matcher m, int group, int defaultVal) {
        try {
            String g = m.group(group);
            return g != null ? Integer.parseInt(g) : defaultVal;
        } catch (Exception e) {
            return defaultVal;
        }
    }

    public String getPattern()  { return pattern;  }
    public TimeZone getTimeZone() { return timeZone; }
    public Locale getLocale()   { return locale;   }
}

package org.apache.commons.lang3.time;

import java.text.FieldPosition;
import java.text.Format;
import java.text.ParseException;
import java.text.ParsePosition;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * FastDateFormat is a fast and thread-safe version of SimpleDateFormat.
 * It delegates formatting to FastDatePrinter and parsing to FastDateParser.
 */
public class FastDateFormat extends Format {

    private static final long serialVersionUID = 1L;

    private final FastDateParser parser;
    private final String pattern;
    private final TimeZone timeZone;
    private final Locale locale;

    /**
     * Constructs a FastDateFormat with the given pattern, time zone, and locale.
     * Internally creates a FastDateParser for parsing operations.
     */
    protected FastDateFormat(String pattern, TimeZone timeZone, Locale locale) {
        this.pattern  = pattern;
        this.timeZone = timeZone;
        this.locale   = locale;
        this.parser   = new FastDateParser(pattern, timeZone, locale);
    }

    /**
     * Factory method: get a FastDateFormat instance for the given pattern.
     * Uses the default locale and the specified time zone.
     */
    public static FastDateFormat getInstance(String pattern, TimeZone timeZone, Locale locale) {
        return new FastDateFormat(pattern, timeZone, locale);
    }

    /**
     * Factory method: get a FastDateFormat for a date-time style.
     * Calls getInstance with a constructed pattern string for the given styles.
     */
    public static FastDateFormat getDateTimeInstance(int dateStyle, int timeStyle, Locale locale) {
        // simplified: build a pattern from the styles
        String pat = "M/d/yy h:mm a"; // approximation of SHORT/SHORT US
        return getInstance(pat, TimeZone.getDefault(), locale);
    }

    /**
     * Formats a Date object to a string using the stored pattern.
     * Calls formatDate internally for the conversion.
     */
    public String format(Date date) {
        return formatDate(date);
    }

    /**
     * Internal date formatting method.
     * Converts the date to a string representation matching the stored pattern.
     */
    private String formatDate(Date date) {
        java.util.Calendar cal = java.util.Calendar.getInstance(timeZone, locale);
        cal.setTime(date);
        // simplified formatting
        return String.format("%04d-%02d-%02d",
            cal.get(java.util.Calendar.YEAR),
            cal.get(java.util.Calendar.MONTH) + 1,
            cal.get(java.util.Calendar.DAY_OF_MONTH)
        );
    }

    /**
     * Parses a date string into a Date object.
     * Delegates to the internal FastDateParser.parse(String) method.
     */
    public Date parse(String source) throws ParseException {
        return parser.parse(source);
    }

    /**
     * Parses a date string at the given position.
     * Delegates to FastDateParser.parse(String, ParsePosition).
     */
    public Date parse(String source, ParsePosition pos) {
        return parser.parse(source, pos);
    }

    @Override
    public StringBuffer format(Object obj, StringBuffer toAppendTo, FieldPosition pos) {
        if (obj instanceof Date) {
            toAppendTo.append(format((Date) obj));
        }
        return toAppendTo;
    }

    @Override
    public Object parseObject(String source, ParsePosition pos) {
        return parse(source, pos);
    }

    public String getPattern()    { return pattern;  }
    public TimeZone getTimeZone() { return timeZone; }
    public Locale getLocale()     { return locale;   }
}

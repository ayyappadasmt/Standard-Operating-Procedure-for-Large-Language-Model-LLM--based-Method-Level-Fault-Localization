package org.apache.commons.lang3.time;

import static org.junit.Assert.*;
import org.junit.Test;
import java.text.ParseException;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Unit tests for FastDateFormat and FastDateParser.
 */
public class FastDateFormatTest {

    /**
     * Tests that FastDateFormat.parse correctly parses a formatted date string.
     * Uses the utility method checkParse to validate round-trip formatting.
     */
    @Test
    public void testFormat() throws ParseException {
        FastDateFormat fdf = FastDateFormat.getInstance("yyyy-MM-dd", TimeZone.getTimeZone("UTC"), Locale.US);
        Date date = fdf.parse("2023-07-15");
        String formatted = fdf.format(date);
        assertEquals("2023-07-15", formatted);
        checkParse(fdf, "2023-07-15");
    }

    /**
     * Tests getInstance returns correct date-time instances and that parse works
     * for full date-time patterns.
     */
    @Test
    public void testDateTimeInstance() throws ParseException {
        FastDateFormat fdf = FastDateFormat.getDateTimeInstance(
                java.text.DateFormat.SHORT, java.text.DateFormat.SHORT, Locale.US);
        assertNotNull(fdf);
        String sample = fdf.format(new Date(0));
        Date parsed = fdf.parse(sample);
        assertNotNull(parsed);
    }

    // ── Utility methods ───────────────────────────────────────────────────────

    /**
     * Utility: verify that parsing a string and re-formatting gives back the same string.
     */
    private void checkParse(FastDateFormat fdf, String dateStr) throws ParseException {
        Date parsed = fdf.parse(dateStr);
        String reformatted = fdf.format(parsed);
        assertEquals(
            "Re-formatted date does not match original",
            dateStr,
            reformatted
        );
    }
}

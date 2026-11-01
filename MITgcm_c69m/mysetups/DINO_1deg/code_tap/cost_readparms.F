#include "COST_OPTIONS.h"

      SUBROUTINE COST_READPARMS( myThid )

c     ==================================================================
c     SUBROUTINE cost_readparms
c     ==================================================================
c
c     o This routine initialises the package cost.
c
c     started: Ralf Giering 18-Jan-2001
c
c     ==================================================================
c     SUBROUTINE cost_readparms
c     ==================================================================

      IMPLICIT NONE

c     == global variables ==
#include "EEPARAMS.h"
#include "SIZE.h"
#include "GRID.h"
#include "PARAMS.h"
#include "cost.h"

c     == routine arguments ==
      INTEGER myThid

c     == local variables ==
      CHARACTER*(max_len_mbuf) msgbuf
      INTEGER iUnit
c     retired parameter
      _RL     mult_depth

c     == end of interface ==

c--   Read the namelist input.
c     cost_atl_jsec and cost_atl_kmaxdepth (DINO_1deg, 2026-10-20): the row
c     and the depth of the section of cost_atlantic_heat.F, which carried
c     them as parameter statements until then (cost.h says what they are).
      NAMELIST /cost_nml/
     &         mult_atl, mult_test, mult_tracer,
     &         cost_atl_jsec, cost_atl_kmaxdepth, cost_atl_quantity,
     &         multTheta, multSalt, multUvel, multVvel, multEtan,
     &         mult_depth,
#ifdef ALLOW_COST_HFLUXM
     &         mult_temp_tut, mult_hflux_tut,
#endif
     &         lastinterval, cost_mask_file

      _BEGIN_MASTER( myThid )

c--     Set default values.
        mult_atl              =      0. _d 0
        mult_test             =      0. _d 0
        mult_tracer           =      0. _d 0
        multTheta             =      0. _d 0
        multSalt              =      0. _d 0
        multUvel              =      0. _d 0
        multVvel              =      0. _d 0
        multEtan              =      0. _d 0
        mult_depth            =      UNSET_RL
#ifdef ALLOW_COST_HFLUXM
        mult_temp_tut         =      0. _d 0
        mult_hflux_tut        =      0. _d 0
#endif
        cost_mask_file        =      ' '
c--     the production section of DINO_1deg since 2026-10-13: the row of the
c--     overturning maximum (centre 43.2 N) and the interface where it peaks
c--     (848 m, 24 levels); a data.cost that sets neither measures that section
        cost_atl_jsec         =      148
        cost_atl_kmaxdepth    =      24
c--     what the section integrates: 'volume' (Sv) or 'heat' (PW; 2026-10-31)
        cost_atl_quantity     =      'volume'

c--     30*24*3600 = 2592000 = 1 model month
        lastinterval = 2592000.

c--     Next, read the cost data file.
        WRITE(msgBuf,'(A)') 'COST_READPARMS: opening data.cost'
        CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                    SQUEEZE_RIGHT , 1)

        CALL OPEN_COPY_DATA_FILE(
     I                          'data.cost', 'COST_READPARMS',
     O                          iUnit,
     I                          myThid )

        READ(  iUnit, nml = cost_nml )

        WRITE(msgBuf,'(A)') 'COST_READPARMS: finished reading data.cost'
        CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                  SQUEEZE_RIGHT , 1)

#ifdef SINGLE_DISK_IO
        CLOSE(iUnit)
#else
        CLOSE(iUnit,STATUS='DELETE')
#endif /* SINGLE_DISK_IO */

        IF ( MOD(lastinterval,deltaTClock) .GT. 0. )
     &       lastinterval = MAX(
     &       INT(lastinterval/deltaTClock-1)*deltaTClock,deltaTClock)


#if (defined ALLOW_COST_HFLUXM) || (defined ALLOW_COST_TEMP)
c-- get the weights for the cost functions
      CALL COST_WEIGHTS( myThid )
cgf : to compile previous line user is expected to provide cost_weights.F
#endif

      IF ( cost_atl_jsec .LT. 1 .OR. cost_atl_jsec .GT. Ny ) THEN
       WRITE(msgBuf,'(A,I6,A,I6,A)')
     & 'S/R COST_READPARMS: cost_atl_jsec =', cost_atl_jsec,
     & ' is not a grid row (1 .. Ny =', Ny, ')'
       CALL PRINT_ERROR( msgBuf, myThid )
       CALL ALL_PROC_DIE( 0 )
       STOP 'ABNORMAL END: S/R COST_READPARMS'
      ENDIF
      IF ( cost_atl_kmaxdepth .LT. 1 .OR. cost_atl_kmaxdepth .GT. Nr ) THEN
       WRITE(msgBuf,'(A,I6,A,I6,A)')
     & 'S/R COST_READPARMS: cost_atl_kmaxdepth =', cost_atl_kmaxdepth,
     & ' is not a level count (1 .. Nr =', Nr, ')'
       CALL PRINT_ERROR( msgBuf, myThid )
       CALL ALL_PROC_DIE( 0 )
       STOP 'ABNORMAL END: S/R COST_READPARMS'
      ENDIF
      IF ( cost_atl_quantity .NE. 'volume' .AND.
     &     cost_atl_quantity .NE. 'heat' ) THEN
       WRITE(msgBuf,'(3A)')
     & 'S/R COST_READPARMS: cost_atl_quantity = ''',
     & cost_atl_quantity, ''' is neither volume nor heat'
       CALL PRINT_ERROR( msgBuf, myThid )
       CALL ALL_PROC_DIE( 0 )
       STOP 'ABNORMAL END: S/R COST_READPARMS'
      ENDIF
      IF ( cost_atl_quantity .EQ. 'heat' .AND.
     &     cost_atl_kmaxdepth .LT. Nr ) THEN
       WRITE(msgBuf,'(A,I3,A,I3,A)')
     & 'S/R COST_READPARMS: WARNING: heat transport over the upper',
     & cost_atl_kmaxdepth, ' of ', Nr, ' levels, not the whole column'
       CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                     SQUEEZE_RIGHT, myThid )
      ENDIF

      IF ( mult_depth .NE. UNSET_RL ) THEN
       WRITE(msgBuf,'(a)')
     & 'S/R COST_READPARMS: mult_depth is now longer allow in data.cost'
       CALL PRINT_ERROR( msgBuf, myThid )
       WRITE(msgBuf,'(a)')
     & 'S/R COST_READPARMS: use generic control cost instead'
       CALL PRINT_ERROR( msgBuf, myThid )
       CALL ALL_PROC_DIE( 0 )
       STOP 'ABNORMAL END: S/R COST_READPARMS'
      ENDIF

C--   print cost parameters to stdout for better debugging
      WRITE(msgBuf,'(A)')
     &'// ======================================================='
      CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                    SQUEEZE_RIGHT, myThid )
      WRITE(msgBuf,'(a)') '// cost configuration  >>> START <<<'
      CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                    SQUEEZE_RIGHT, myThid )
      WRITE(msgBuf,'(A)')
     &'// ======================================================='
      CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                    SQUEEZE_RIGHT, myThid )

      CALL WRITE_0D_RL( lastinterval, INDEX_NONE,'lastinterval =',
     &'   /* cost interval over which to average ( s ). */')
C
       CALL WRITE_0D_C( cost_mask_file, -1, INDEX_NONE,
     &  'cost_mask_file =', ' /* file name of cost mask file */')
      CALL WRITE_0D_I( cost_atl_jsec, INDEX_NONE, 'cost_atl_jsec =',
     &'   /* row whose southern face the section integrates across */')
      CALL WRITE_0D_I( cost_atl_kmaxdepth, INDEX_NONE,
     &'cost_atl_kmaxdepth =',
     &'   /* levels integrated from the surface (section depth) */')
      CALL WRITE_0D_C( cost_atl_quantity, -1, INDEX_NONE,
     &'cost_atl_quantity =',
     &'   /* volume (Sv) or heat (PW) across the section */')

      WRITE(msgBuf,'(A)')
     &'// ======================================================='
      CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                    SQUEEZE_RIGHT, myThid )
      WRITE(msgBuf,'(A)') '// cost configuration  >>> END <<<'
      CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                    SQUEEZE_RIGHT, myThid )
      WRITE(msgBuf,'(A)')
     &'// ======================================================='
      CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                    SQUEEZE_RIGHT, myThid )
      WRITE(msgBuf,'(A)') ' '
      CALL PRINT_MESSAGE( msgBuf, standardMessageUnit,
     &                    SQUEEZE_RIGHT, myThid )

      _END_MASTER( myThid )

      _BARRIER

      RETURN
      END

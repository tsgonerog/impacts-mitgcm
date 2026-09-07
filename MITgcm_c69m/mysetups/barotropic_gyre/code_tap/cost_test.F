#include "COST_OPTIONS.h"

      SUBROUTINE COST_TEST( myThid )
C     *==========================================================*
C     | SUBROUTINE COST_TEST                                     |
C     | Setup-specific version (mysetups/barotropic_gyre) of     |
C     | pkg/cost/cost_test.F: the mean surface temperature over  |
C     | a fixed box, evaluated at the final time step. Upstream's |
C     | version measures theta at the single grid point (80,30), |
C     | which lies outside this 62 x 62 domain. Same routine     |
C     | name, same objf_test / mult_test plumbing, so no other   |
C     | file changes; the box is compiled in, like the section   |
C     | of DINO's cost_atlantic_heat.F.                          |
C     *==========================================================*
      IMPLICIT NONE
#include "SIZE.h"
#include "EEPARAMS.h"
#include "PARAMS.h"
#include "DYNVARS.h"
#include "GRID.h"
#include "cost.h"
      INTEGER myThid
#ifdef ALLOW_COST_TEST
C     The target box, in global cell indices: the ocean occupies cells
C     2..61 in both directions (cells 1 and 62 are walls); the box is
C     10 x 10 cells = 200 km x 200 km over the northern part of the
C     western boundary current (x = 60..260 km, y = 780..980 km), where
C     the flow is strongest and the sensitivity is carried upstream.
      INTEGER iBoxLo, iBoxHi, jBoxLo, jBoxHi
      PARAMETER ( iBoxLo = 5, iBoxHi = 14, jBoxLo = 40, jBoxHi = 49 )
      INTEGER bi, bj, i, j, ig, jg
      _RL nBox
      nBox = (iBoxHi-iBoxLo+1)*(jBoxHi-jBoxLo+1)
      DO bj = myByLo(myThid), myByHi(myThid)
       DO bi = myBxLo(myThid), myBxHi(myThid)
        DO j = 1, sNy
         jg = myYGlobalLo-1+(bj-1)*sNy+j
         DO i = 1, sNx
          ig = myXGlobalLo-1+(bi-1)*sNx+i
          IF ( ig.GE.iBoxLo .AND. ig.LE.iBoxHi .AND.
     &         jg.GE.jBoxLo .AND. jg.LE.jBoxHi ) THEN
           objf_test(bi,bj) = objf_test(bi,bj)
     &                      + theta(i,j,1,bi,bj)*maskC(i,j,1,bi,bj)/nBox
          ENDIF
         ENDDO
        ENDDO
       ENDDO
      ENDDO
#endif /* ALLOW_COST_TEST */
      RETURN
      END
